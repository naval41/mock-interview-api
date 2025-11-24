"""
Design Context Processor implementation that extends BaseProcessor.
"""

import asyncio
import time
from pipecat.frames.frames import Frame, LLMMessagesAppendFrame
from pipecat.processors.frame_processor import FrameDirection
from pipecat.processors.frameworks.rtvi import RTVIClientMessageFrame
from app.interview_playground.processors.base_processor import BaseProcessor
from app.interview_playground.utility_functions.parse_design_diagrams import (
    ExcalidrawParser,
    DescriptionGenerator,
    MermaidGenerator
)
from app.interview_playground.manager.design_diff_manager import DesignDiffManager
from app.models.enums import ToolEvent
import structlog
import json

logger = structlog.get_logger()

class DesignContextProcessor(BaseProcessor):
    """Design Context Processor for handling design-related messages and context."""
    
    def __init__(self, max_design_elements: int = 15, design_patterns: bool = True, debounce_seconds: int = 30):
        """Initialize Design Context Processor.
        
        Args:
            max_design_elements: Maximum number of design elements to keep in context
            design_patterns: Whether to detect design patterns
            debounce_seconds: Seconds to wait before sending design to LLM (default: 30)
        """
        super().__init__(name="design_context_processor")
        self.max_design_elements = max_design_elements
        self.design_patterns = design_patterns
        self.design_elements = []
        self.design_context = {}
        self.debounce_seconds = debounce_seconds
        
        # Debounce mechanism
        self.pending_design_submission = None  # Stores latest pending submission
        self.debounce_task = None              # Asyncio task for debounced submission
        self.last_activity_time = 0            # Timestamp of last design activity
        self.submission_count = 0              # Track number of submissions
        
        # Change detection - track both pending and completed
        self.last_submitted_description = None  # Last successfully sent to LLM
        self.last_submitted_mermaid = None      # Last successfully sent to LLM
        self.last_pending_description = None    # Last pending (may not be sent yet)
        self.last_pending_mermaid = None        # Last pending (may not be sent yet)
        
        # Initialize Excalidraw parser utilities
        self.parser = ExcalidrawParser()
        self.description_generator = DescriptionGenerator()
        self.mermaid_generator = MermaidGenerator()
        
        # Initialize design diff manager for database operations
        self.design_diff_manager = DesignDiffManager()
        
        logger.info("DesignContextProcessor initialized with Excalidraw parser utilities and DB manager",
                   debounce_seconds=debounce_seconds)
        
    # Remove the setup_processor method - it's no longer needed
    
    async def process_custom_frame(self, frame: Frame, direction: FrameDirection):
        """Process frames after StartFrame validation."""
        if isinstance(frame, RTVIClientMessageFrame) and frame.type == ToolEvent.DESIGN_CONTENT:
            logger.info("RTVI Design frame Content", frame=frame)
            await self._process_design_content(frame)
        else:
            # Continue processing the frame
            await self.push_frame(frame, direction)

    
    async def _process_design_content(self, frame: RTVIClientMessageFrame):
        """Process design content using the Excalidraw parser utility."""
        logger.info("Processing design content", frame=frame)
        data = frame.data or {}
        content = data.get("content", "")
        
        # Try to parse as JSON (Excalidraw format)
        try:
            # Check if content is a string that needs JSON parsing
            if isinstance(content, str):
                try:
                    json_data = json.loads(content)
                    logger.info("Parsed content as JSON", content_type="excalidraw_json")
                except json.JSONDecodeError:
                    logger.warning("Content is not valid JSON, treating as plain text")
                    json_data = None
            else:
                # Content is already a dict/object
                json_data = content
                logger.info("Content is already parsed JSON", content_type="excalidraw_json")
            
            # Process based on content type
            if json_data and isinstance(json_data, dict):
                # Process Excalidraw JSON
                await self._process_excalidraw_json(frame, json_data)
            else:
                # Process as plain text
                await self._process_plain_text(frame, content)
                
        except Exception as e:
            logger.error("Failed to process design content", error=str(e), error_type=type(e).__name__)
    
    async def _process_excalidraw_json(self, frame: RTVIClientMessageFrame, json_data: dict):
        """Process Excalidraw JSON data using parser utilities with debounce logic.
        
        Args:
            frame: The RTVI client message frame
            json_data: Parsed Excalidraw JSON data
        """
        try:
            # Extract metadata from frame
            data = frame.data or {}
            question_id = data.get("questionId", "")
            candidate_interview_id = data.get("candidateInterviewId", "")
            timestamp = data.get("timestamp")
            
            logger.info("Processing Excalidraw design",
                       question_id=question_id,
                       candidate_interview_id=candidate_interview_id)
            
            # Parse the Excalidraw diagram to structure
            structure = self.parser.parse_to_structure(json_data)
            
            logger.info("Excalidraw diagram parsed successfully",
                       component_count=len(structure.components),
                       connection_count=len(structure.connections),
                       standalone_count=len(structure.standalone_elements))
            
            # Generate description
            description = self.description_generator.generate(structure)
            
            # Generate Mermaid diagram
            mermaid_diagram = self.mermaid_generator.generate(structure)

            logger.info("Generated Description", description=description)
            logger.info("Generated Mermaid diagram", mermaid_diagram=mermaid_diagram)
            
            # Check for changes
            has_changes, change_type = self._has_design_changes(description, mermaid_diagram)
            
            if has_changes:
                logger.info(f"Design {change_type} detected - using debounce mechanism",
                           change_type=change_type,
                           debounce_seconds=self.debounce_seconds)
                
                # Extract design elements from components
                for component in structure.components:
                    if component.label and component.label.text:
                        self._add_design_element(
                            [component.label.text],
                            "excalidraw_component"
                        )
                
                # Store parsed diagram info (for reference)
                frame_id = str(frame.id) if hasattr(frame, 'id') else 'unknown'
                self.design_context[frame_id] = {
                    "diagram_type": "excalidraw",
                    "component_count": len(structure.components),
                    "connection_count": len(structure.connections),
                    "description": description,
                    "mermaid": mermaid_diagram,
                    "structure": structure,
                    "original_json": json_data,  # Store original for DB
                    "question_id": question_id,
                    "candidate_interview_id": candidate_interview_id,
                    "timestamp": timestamp
                }
                
                logger.info("Excalidraw diagram context stored", frame_id=frame_id)
                
                # Schedule debounced LLM submission
                self._schedule_debounced_submission(
                    structure, description, mermaid_diagram, frame_id,
                    json_data, question_id, candidate_interview_id, timestamp
                )
            else:
                logger.debug("No design changes detected, skipping debounce scheduling")
            
        except Exception as e:
            logger.error("Failed to process Excalidraw JSON",
                        error=str(e),
                        error_type=type(e).__name__)
    
    async def _process_plain_text(self, frame: RTVIClientMessageFrame, content: str):
        """Process plain text design content (legacy fallback).
        
        Args:
            frame: The RTVI client message frame
            content: Plain text content
        """
        logger.info("Processing as plain text design content", content_length=len(content))
        
        # Extract design elements using pattern matching
        design_elements = self._extract_design_elements(content)
        design_type = self._detect_design_type(content)
        
        if design_elements:
            logger.info("Extracted design elements from text",
                       element_count=len(design_elements),
                       design_type=design_type)
            
            self._add_design_element(design_elements, design_type)
            
            # Store plain text design info
            frame_id = str(frame.id) if hasattr(frame, 'id') else 'unknown'
            self.design_context[frame_id] = {
                "diagram_type": "plain_text",
                "design_type": design_type,
                "elements": design_elements,
                "content": content[:500]  # Store first 500 chars
            }
        else:
            logger.warning("No design elements extracted from plain text")
    
    def _has_design_changes(self, new_description: str, new_mermaid: str) -> tuple:
        """Check if design has changed from last submission.
        
        Args:
            new_description: New design description
            new_mermaid: New mermaid diagram
            
        Returns:
            Tuple of (has_changes: bool, change_type: str)
            change_type can be: "first_submission", "incremental_update", or "no_change"
        """
        # Determine what to compare against - prefer pending, fallback to submitted
        compare_description = self.last_pending_description or self.last_submitted_description
        compare_mermaid = self.last_pending_mermaid or self.last_submitted_mermaid
        
        # First submission case - nothing to compare against
        if compare_description is None:
            logger.info("🔍 Change Detection: FIRST SUBMISSION",
                       new_description_length=len(new_description),
                       new_mermaid_length=len(new_mermaid))
            logger.info("📝 New Description:", description=new_description)
            logger.info("🎨 New Mermaid:", mermaid=new_mermaid)
            return (True, "first_submission")
        
        # Compare description and mermaid against the reference (pending or submitted)
        description_changed = new_description != compare_description
        mermaid_changed = new_mermaid != compare_mermaid
        
        # Log detailed comparison
        comparing_against = "pending" if self.last_pending_description else "submitted"
        logger.info("🔍 Change Detection: COMPARING WITH PREVIOUS",
                   description_changed=description_changed,
                   mermaid_changed=mermaid_changed,
                   comparing_against=comparing_against)
        
        if description_changed:
            logger.info("📝 Description CHANGED:")
            logger.info("════════════════════════════════════════════════════════════")
            logger.info(f"PREVIOUS Description ({comparing_against}):")
            logger.info(compare_description)
            logger.info("────────────────────────────────────────────────────────────")
            logger.info("CURRENT Description:")
            logger.info(new_description)
            logger.info("════════════════════════════════════════════════════════════")
            prev_len = len(compare_description) if compare_description else 0
            logger.info("Comparison:",
                       previous_length=prev_len,
                       current_length=len(new_description),
                       length_diff=len(new_description) - prev_len)
        else:
            logger.info("📝 Description: NO CHANGE",
                       length=len(new_description))
        
        if mermaid_changed:
            logger.info("🎨 Mermaid CHANGED:")
            logger.info("════════════════════════════════════════════════════════════")
            logger.info(f"PREVIOUS Mermaid ({comparing_against}):")
            logger.info(compare_mermaid)
            logger.info("────────────────────────────────────────────────────────────")
            logger.info("CURRENT Mermaid:")
            logger.info(new_mermaid)
            logger.info("════════════════════════════════════════════════════════════")
            prev_len = len(compare_mermaid) if compare_mermaid else 0
            curr_len = len(new_mermaid)
            logger.info("Comparison:",
                       previous_length=prev_len,
                       current_length=curr_len,
                       length_diff=curr_len - prev_len)
        else:
            logger.info("🎨 Mermaid: NO CHANGE",
                       length=len(new_mermaid))
        
        if description_changed or mermaid_changed:
            logger.info("✅ RESULT: Changes detected - will trigger debounce",
                       reason="description" if description_changed else "mermaid")
            return (True, "incremental_update")
        
        logger.info("⛔ RESULT: No changes detected - skipping debounce")
        return (False, "no_change")
    
    def _schedule_debounced_submission(
        self, structure, description: str, mermaid: str, frame_id: str,
        original_json: dict, question_id: str, candidate_interview_id: str, timestamp
    ):
        """Schedule or reschedule a debounced submission to LLM.
        
        Cancels existing task if new design activity detected.
        
        Args:
            structure: Parsed diagram structure
            description: Generated description
            mermaid: Generated mermaid diagram
            frame_id: Frame identifier
            original_json: Original Excalidraw JSON
            question_id: Question ID
            candidate_interview_id: Candidate interview ID
            timestamp: Submission timestamp
        """
        current_time = time.time()
        self.last_activity_time = current_time
        
        # Cancel existing debounce task
        if self.debounce_task and not self.debounce_task.done():
            self.debounce_task.cancel()
            logger.debug("Cancelled previous debounce - new design activity detected")
        
        # Store latest submission data
        self.pending_design_submission = {
            'structure': structure,
            'description': description,
            'mermaid': mermaid,
            'frame_id': frame_id,
            'original_json': original_json,
            'question_id': question_id,
            'candidate_interview_id': candidate_interview_id,
            'timestamp': timestamp,
            'activity_time': current_time
        }
        
        # Update pending values immediately (for comparison on next frame)
        self.last_pending_description = description
        self.last_pending_mermaid = mermaid
        
        logger.info("📌 Updated pending reference for change detection",
                   pending_description_length=len(description),
                   pending_mermaid_length=len(mermaid),
                   question_id=question_id)
        
        # Create new debounce task
        self.debounce_task = asyncio.create_task(
            self._debounced_llm_submission(
                description, mermaid, frame_id, 
                original_json, question_id, candidate_interview_id, timestamp
            )
        )
        
        logger.info(f"⏳ Design activity detected - scheduling LLM submission in {self.debounce_seconds}s",
                   frame_id=frame_id,
                   question_id=question_id,
                   activity_time=current_time)
    
    async def _debounced_llm_submission(
        self, description: str, mermaid: str, frame_id: str,
        original_json: dict, question_id: str, candidate_interview_id: str, timestamp
    ):
        """Handle debounced submission to LLM after inactivity period.
        
        Waits for debounce_seconds, then stores to database and sends design to LLM.
        
        Args:
            description: Design description
            mermaid: Mermaid diagram
            frame_id: Frame identifier
            original_json: Original Excalidraw JSON
            question_id: Question ID
            candidate_interview_id: Candidate interview ID
            timestamp: Submission timestamp
        """
        try:
            await asyncio.sleep(self.debounce_seconds)
            
            # Check if this is still the latest submission
            if (self.pending_design_submission and 
                self.pending_design_submission['description'] == description):
                
                self.submission_count += 1
                
                logger.info(f"🕒 Debounce completed - storing design and sending to LLM",
                           submission_count=self.submission_count,
                           debounce_seconds=self.debounce_seconds,
                           frame_id=frame_id,
                           question_id=question_id)
                
                # Store design in database using diff manager
                try:
                    diff_result = await self.design_diff_manager.process_design_content(
                        question_id=question_id,
                        candidate_interview_id=candidate_interview_id,
                        design_content=original_json,
                        description=description,
                        mermaid=mermaid,
                        timestamp=timestamp
                    )
                    
                    logger.info("💾 Design stored in database",
                               solution_id=diff_result.solution_id,
                               question_id=question_id,
                               is_first_submission=diff_result.is_first_submission)
                    
                except Exception as db_error:
                    logger.error("Failed to store design in database",
                                error=str(db_error),
                                question_id=question_id)
                    # Continue with LLM submission even if DB fails
                
                # Build LLM prompt
                llm_prompt = self._build_llm_prompt(description, mermaid)
                
                messages = [
                    {
                        "role": "user",
                        "content": llm_prompt
                    }
                ]
                
                # Send to LLM
                await self.push_frame(
                    LLMMessagesAppendFrame(messages=messages, run_llm=True),
                    FrameDirection.DOWNSTREAM
                )
                
                # Update last submitted content (move pending to submitted)
                self.last_submitted_description = description
                self.last_submitted_mermaid = mermaid
                
                # Clear pending submission (it's now submitted)
                self.pending_design_submission = None
                self.last_pending_description = None
                self.last_pending_mermaid = None
                
                logger.info("✅ Design successfully sent to LLM after debounce",
                           frame_id=frame_id,
                           question_id=question_id,
                           submission_count=self.submission_count)
                logger.info("📌 Moved pending to submitted reference",
                           submitted_description_length=len(description),
                           submitted_mermaid_length=len(mermaid))
            else:
                logger.debug("Debounce cancelled - newer submission received")
                
        except asyncio.CancelledError:
            logger.debug("Debounce task cancelled - newer submission received")
        except Exception as e:
            logger.error("Error in debounced LLM submission", error=str(e))
    
    def _build_llm_prompt(self, description: str, mermaid: str) -> str:
        """Build LLM prompt with design description and diagram.
        
        Different prompts for first submission vs incremental updates.
        
        Args:
            description: Design description
            mermaid: Mermaid diagram
            
        Returns:
            Formatted prompt string for LLM
        """
        is_first = self.last_submitted_description is None
        
        if is_first:
            # First submission prompt
            prompt = f"""
📐 **CANDIDATE DESIGN SUBMISSION - INITIAL DESIGN**

The candidate has been working on their design diagram and after a period of activity, here is their current design:

**Submission Count:** {self.submission_count}

**Design Description:**
{description}

**Diagram Structure (Mermaid):**
```mermaid
{mermaid}
```

**Context:**
- This is the candidate's first design submission after {self.debounce_seconds} seconds of inactivity
- The candidate has been actively designing and this represents their current thinking
- This design may be incomplete, in development, or represent their initial approach
- The diagram is captured after a natural pause in their design activity

**Instructions:**
- Review the design structure and components
- Assess the overall architecture and relationships
- Consider the clarity and organization of the design
- This is likely an early-stage design, allow for natural development

**Response Guidelines:**
- This is a reference update - respond only if meaningful feedback is warranted
- Consider this an ongoing design process, not a final submission
- Look for major structural issues but allow iterative refinement
"""
        else:
            # Incremental update prompt
            prompt = f"""
🔄 **CANDIDATE DESIGN SUBMISSION - INCREMENTAL UPDATE**

The candidate has continued working on their design with incremental changes:

**Submission Count:** {self.submission_count}

**Updated Design Description:**
{description}

**Updated Diagram Structure (Mermaid):**
```mermaid
{mermaid}
```

**Context:**
- This is an incremental update after {self.debounce_seconds} seconds of inactivity
- The candidate has been refining and evolving their design
- This represents their evolved thinking since the last submission

**Instructions:**
- Compare with conceptual understanding of previous design (if you recall it)
- Assess the design evolution and refinement
- Look for signs of design maturity and completeness
- The candidate is iteratively building their design

**Response Guidelines:**
- If the design appears substantially complete:
  * Provide constructive feedback on architecture and structure
  * Ask thoughtful questions about design decisions
  * Discuss scalability, maintainability, or alternative approaches
- If still in development:
  * Observe iterative progress
  * Allow continued natural development
  * Intervene only for critical structural issues
"""
        
        logger.info("Built LLM prompt",
                   is_first_submission=is_first,
                   prompt_length=len(prompt))
        
        return prompt.strip()
        
    def _extract_design_elements(self, message: str) -> list:
        """Extract design elements from a message.
        
        Args:
            message: Message to extract design elements from
            
        Returns:
            List of design elements found
        """
        # Simple design element detection - look for common patterns
        design_patterns = [
            "UI/UX", "user interface", "user experience", "wireframe", "mockup",
            "prototype", "design system", "component", "layout", "typography",
            "color scheme", "visual hierarchy", "information architecture",
            "user flow", "interaction design", "responsive design", "accessibility",
            "usability", "user research", "persona", "user journey", "storyboard"
        ]
        
        design_elements = []
        message_lower = message.lower()
        
        for pattern in design_patterns:
            if pattern in message_lower:
                design_elements.append(pattern)
                
        return design_elements
        
    def _detect_design_type(self, message: str) -> str:
        """Detect design type from message.
        
        Args:
            message: Message to analyze
            
        Returns:
            Detected design type
        """
        # Simple design type detection based on keywords
        design_types = {
            "ui_ux": ["ui", "ux", "user interface", "user experience", "wireframe", "mockup"],
            "interaction": ["interaction", "user flow", "user journey", "storyboard", "prototype"],
            "visual": ["visual", "typography", "color", "layout", "hierarchy", "design system"],
            "research": ["research", "persona", "usability", "user research", "testing"],
            "accessibility": ["accessibility", "a11y", "inclusive", "universal design"],
            "responsive": ["responsive", "mobile", "adaptive", "flexible layout"]
        }
        
        message_lower = message.lower()
        
        for design_type, keywords in design_types.items():
            if any(keyword in message_lower for keyword in keywords):
                return design_type
                
        return "general"
        
    def _add_design_element(self, design_elements: list, design_type: str):
        """Add design elements to context.
        
        Args:
            design_elements: List of design elements to add
            design_type: Type of design elements
        """
        for element in design_elements:
            self.design_elements.append({
                "element": element,
                "type": design_type,
                "timestamp": "now"  # In real implementation, use actual timestamp
            })
            
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
        
    def get_design_patterns(self) -> dict:
        """Get detected design patterns.
        
        Returns:
            Dictionary of design patterns by type
        """
        patterns = {}
        for element in self.design_elements:
            design_type = element["type"]
            if design_type not in patterns:
                patterns[design_type] = []
            patterns[design_type].append(element["element"])
            
        return patterns
        
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
            "design_types_found": list(set(element["type"] for element in self.design_elements))
        }
