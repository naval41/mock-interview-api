"""
Design Context Processor implementation that extends BaseProcessor.

Consumes the canvas payload as sent. The browser builds the semantic graph, so it
already knows the component types, the connection protocols and the annotations,
and it emits the prose and the Mermaid itself — there is nothing left here to
interpret. This replaced a vendored Excalidraw parser that reconstructed meaning
from rectangle coordinates and arrow endpoints: 13 modules of geometry heuristics
guessing at facts the canvas had all along.

Two consequences worth knowing:

  - There is no debounce here. The canvas waits for a pause before sending, so a
    second timer on this side only delayed the interviewer's view of the design.
    The old pair (10s in the browser, 30s here) meant a design could take most of
    a minute to reach the bot.

  - A payload that is not `design-graph-v1` is dropped with a warning rather than
    guessed at. The previous fallback ran a keyword matcher over the raw bytes,
    which is how a compression bug went unnoticed: the browser gzipped the scene,
    `json.loads` could not read it, and every design quietly took the text path
    and matched nothing.
"""

from pipecat.frames.frames import Frame, LLMMessagesAppendFrame
from pipecat.processors.frame_processor import FrameDirection
from pipecat.processors.frameworks.rtvi import RTVIClientMessageFrame
from app.interview_playground.processors.base_processor import BaseProcessor
from app.interview_playground.manager.design_diff_manager import DesignDiffManager
from app.models.enums import ToolEvent
import structlog
import json

logger = structlog.get_logger()

DESIGN_PAYLOAD_FORMAT = "design-graph-v1"


class DesignContextProcessor(BaseProcessor):
    """Design Context Processor for handling design-related messages and context."""

    def __init__(self, max_design_elements: int = 15, design_patterns: bool = True):
        """Initialize Design Context Processor.

        Args:
            max_design_elements: Maximum number of design elements to keep in context
            design_patterns: Whether to detect design patterns
        """
        super().__init__(name="design_context_processor")
        self.max_design_elements = max_design_elements
        self.design_patterns = design_patterns
        self.design_elements = []
        self.design_context = {}
        self.submission_count = 0

        # Change detection. The canvas suppresses no-op changes already — moving a
        # box does not resend — but a reconnect replays the current design, so an
        # exact comparison here keeps that from re-prompting the interviewer.
        self.last_submitted_description = None
        self.last_submitted_mermaid = None

        self.design_diff_manager = DesignDiffManager()

        logger.info("DesignContextProcessor initialized")

    async def process_custom_frame(self, frame: Frame, direction: FrameDirection):
        """Process frames after StartFrame validation."""
        if isinstance(frame, RTVIClientMessageFrame) and frame.type == ToolEvent.DESIGN_CONTENT:
            await self._process_design_content(frame)
        else:
            # Continue processing the frame
            await self.push_frame(frame, direction)

    async def _process_design_content(self, frame: RTVIClientMessageFrame):
        """Route a design frame to the payload handler."""
        data = frame.data or {}
        content = data.get("content")

        # The canvas sends an object; a string is accepted only because the
        # end-of-interview flush serializes the payload before handing it over.
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except json.JSONDecodeError:
                logger.warning(
                    "Design content is not valid JSON - dropping frame",
                    content_length=len(content),
                )
                return

        if not isinstance(content, dict):
            logger.warning(
                "Design content is not an object - dropping frame",
                content_type=type(content).__name__,
            )
            return

        if content.get("format") != DESIGN_PAYLOAD_FORMAT:
            logger.warning(
                "Unrecognised design payload format - dropping frame",
                received_format=content.get("format"),
                expected_format=DESIGN_PAYLOAD_FORMAT,
            )
            return

        await self._process_design_payload(frame, content)

    async def _process_design_payload(self, frame: RTVIClientMessageFrame, payload: dict):
        """Store the design and hand it to the interviewer.

        Args:
            frame: The RTVI client message frame
            payload: A `design-graph-v1` payload from the canvas
        """
        try:
            data = frame.data or {}
            question_id = data.get("questionId", "")
            candidate_interview_id = data.get("candidateInterviewId", "")
            timestamp = data.get("timestamp")
            is_final = bool(data.get("isFinal"))

            graph = payload.get("graph") or {}
            description = payload.get("description") or ""
            mermaid = payload.get("mermaid") or ""
            stats = payload.get("stats") or {}

            logger.info(
                "Processing design payload",
                question_id=question_id,
                candidate_interview_id=candidate_interview_id,
                is_final=is_final,
                node_count=stats.get("nodes"),
                edge_count=stats.get("edges"),
                annotation_count=stats.get("annotations"),
            )

            # The final flush is stored even when unchanged: it is the last word on
            # what the candidate left on the canvas, and the round is over, so there
            # is no interviewer turn left to protect from a redundant prompt.
            unchanged = (
                description == self.last_submitted_description
                and mermaid == self.last_submitted_mermaid
            )
            if unchanged and not is_final:
                logger.debug("No design changes detected - skipping", question_id=question_id)
                return

            for node in graph.get("nodes") or []:
                label = node.get("label") or node.get("customType")
                if label:
                    self._add_design_element([label], "design_component")

            frame_id = str(frame.id) if hasattr(frame, "id") else "unknown"
            self.design_context[frame_id] = {
                "diagram_type": "design_graph",
                "component_count": stats.get("nodes", 0),
                "connection_count": stats.get("edges", 0),
                "description": description,
                "mermaid": mermaid,
                "graph": graph,
                "question_id": question_id,
                "candidate_interview_id": candidate_interview_id,
                "timestamp": timestamp,
            }

            await self._store_design(
                question_id=question_id,
                candidate_interview_id=candidate_interview_id,
                graph=graph,
                description=description,
                mermaid=mermaid,
                timestamp=timestamp,
            )

            # Nothing to say to the interviewer about a design that has not moved,
            # and the round is over on the final flush.
            if not unchanged and not is_final:
                await self._submit_to_llm(description, mermaid, question_id, frame_id)

            self.last_submitted_description = description
            self.last_submitted_mermaid = mermaid

        except Exception as e:
            logger.error(
                "Failed to process design payload",
                error=str(e),
                error_type=type(e).__name__,
            )

    async def _store_design(
        self,
        question_id: str,
        candidate_interview_id: str,
        graph: dict,
        description: str,
        mermaid: str,
        timestamp,
    ):
        """Persist the design, and carry on to the interviewer if it fails.

        A failed write costs a reviewer the diagram on the feedback page later; a
        skipped prompt costs the candidate the interviewer's attention now, which is
        the worse of the two.
        """
        try:
            diff_result = await self.design_diff_manager.process_design_content(
                question_id=question_id,
                candidate_interview_id=candidate_interview_id,
                design_content=graph,
                description=description,
                mermaid=mermaid,
                timestamp=timestamp,
            )
            logger.info(
                "💾 Design stored in database",
                solution_id=diff_result.solution_id,
                question_id=question_id,
                is_first_submission=diff_result.is_first_submission,
            )
        except Exception as db_error:
            logger.error(
                "Failed to store design in database",
                error=str(db_error),
                question_id=question_id,
            )

    async def _submit_to_llm(
        self, description: str, mermaid: str, question_id: str, frame_id: str
    ):
        """Append the design to the interviewer's context and let it respond."""
        self.submission_count += 1
        messages = [{"role": "user", "content": self._build_llm_prompt(description, mermaid)}]

        await self.push_frame(
            LLMMessagesAppendFrame(messages=messages, run_llm=True),
            FrameDirection.DOWNSTREAM,
        )

        logger.info(
            "✅ Design sent to LLM",
            frame_id=frame_id,
            question_id=question_id,
            submission_count=self.submission_count,
        )

    def _build_llm_prompt(self, description: str, mermaid: str) -> str:
        """Build the prompt carrying the candidate's current design.

        The description leads and the Mermaid follows. The description is the fuller
        record — it spells out per-node properties, annotations, whether a link is
        mutually authenticated or crosses a trust boundary, and which parts came
        from the copilot, none of which Mermaid has syntax for. The diagram is
        included because shape reads faster than a list when the question is "what
        talks to what".

        Args:
            description: Design description, as the canvas wrote it
            mermaid: Mermaid diagram, as the canvas wrote it

        Returns:
            Formatted prompt string for LLM
        """
        is_first = self.last_submitted_description is None
        heading = (
            "📐 **CANDIDATE DESIGN — INITIAL SUBMISSION**"
            if is_first
            else "🔄 **CANDIDATE DESIGN — UPDATED**"
        )

        prompt = f"""
{heading}

**Submission Count:** {self.submission_count}

**Design:**
{description}

**Diagram Structure (Mermaid):**
```mermaid
{mermaid}
```

**Context:**
- This is the candidate's design as it stands right now, sent after a pause in
  their drawing — not a finished submission
- They are still working; treat gaps as unfinished rather than as omissions

**Response Guidelines:**
- Respond only if there is something worth saying; silence is a valid response to
  a design that is simply progressing
- Probe design decisions, scalability and alternatives once the shape is settled
- Raise structural problems early, but leave room for iteration
"""

        logger.info("Built LLM prompt", is_first_submission=is_first, prompt_length=len(prompt))

        return prompt.strip()

    def _add_design_element(self, design_elements: list, design_type: str):
        """Add design elements to context.

        Args:
            design_elements: List of design elements to add
            design_type: Type of design elements
        """
        for element in design_elements:
            self.design_elements.append(
                {
                    "element": element,
                    "type": design_type,
                }
            )

        # Keep only the last max_design_elements
        if len(self.design_elements) > self.max_design_elements:
            self.design_elements = self.design_elements[-self.max_design_elements:]

    def get_design_context(self) -> list:
        """Get the current design context.

        Returns:
            List of design elements in context
        """
        return self.design_elements.copy()

    def clear_design_context(self):
        """Clear all design elements from context."""
        self.design_elements.clear()

    def get_status(self) -> dict:
        """Get the current status of the design context processor.

        Returns:
            Dictionary containing design context processor status
        """
        return {
            "type": "design_context",
            "design_elements_count": len(self.design_elements),
            "max_design_elements": self.max_design_elements,
            "design_patterns": self.design_patterns,
            "submission_count": self.submission_count,
        }
