"""
ContextSwitchProcessor for managing LLM instruction transitions during interview phases.
"""

from datetime import datetime
from pipecat.frames.frames import Frame, TextFrame, LLMMessagesUpdateFrame
from pipecat.processors.frame_processor import FrameDirection
from pipecat.processors.frameworks.rtvi import RTVIClientMessageFrame
from app.interview_playground.processors.base_processor import BaseProcessor
from app.entities.interview_context import InterviewContext, PlannerField
import structlog

logger = structlog.get_logger()


class ContextSwitchProcessor(BaseProcessor):
    """Processor for managing LLM instruction transitions during interview phases."""
    
    def __init__(self, interview_context: InterviewContext):
        """Initialize ContextSwitchProcessor.
        
        Args:
            interview_context: The interview context containing planner fields
        """
        super().__init__(name="context_switch_processor")
        self.interview_context = interview_context
        self.current_instructions = ""
        self.phase_transition_count = 0
        self.logger = logger.bind(
            mock_interview_id=interview_context.mock_interview_id,
            session_id=interview_context.session_id
        )
        
        self.logger.info("ContextSwitchProcessor initialized", 
                        planner_fields_count=len(interview_context.planner_fields))
    
    async def process_custom_frame(self, frame: Frame, direction: FrameDirection):
        """Process frames after StartFrame validation."""
        # Handle RTVI client messages and other frames as needed
        if isinstance(frame, RTVIClientMessageFrame):
            self.logger.debug("RTVI client message received in context switch processor")
        
        # Continue processing the frame
        await self.push_frame(frame, direction)
    
    async def inject_planner_instructions(self, planner_field: PlannerField):
        """Inject new planner instructions into LLM context.
        
        Args:
            planner_field: The planner field containing instructions to inject
        """
        try:
            instructions = planner_field.interview_instructions or self._get_default_instructions()
            
            # Create system message frame with new instructions
            system_message = self._create_transition_message(instructions, planner_field)
            
            # Create LLM message frame to inject context
            context_frame = self._create_llm_context_frame(system_message)
            
            # Push the context frame downstream to LLM
            await self.push_frame(context_frame, FrameDirection.DOWNSTREAM)
            
            self.current_instructions = instructions
            self.phase_transition_count += 1
            
            self.logger.info("Injected planner instructions", 
                           sequence=planner_field.sequence,
                           duration_minutes=planner_field.duration,
                           question_id=planner_field.question_id,
                           instructions_length=len(instructions),
                           transition_count=self.phase_transition_count)
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to inject planner instructions", 
                            sequence=planner_field.sequence,
                            error=str(e))
            return False
    
    async def inject_interview_closure_context(self):
        """Inject interview closure instructions when all planners are complete."""
        try:
            closure_instructions = self._get_interview_closure_instructions()
            
            # Create closure message
            closure_message = self._create_closure_message(closure_instructions)
            
            # Create LLM context frame
            context_frame = self._create_llm_context_frame(closure_message)
            
            # Push closure context downstream
            await self.push_frame(context_frame, FrameDirection.DOWNSTREAM)
            
            self.current_instructions = closure_instructions
            
            self.logger.info("Injected interview closure context", 
                           total_transitions=self.phase_transition_count)
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to inject interview closure context", error=str(e))
            return False
    
    def get_current_instructions(self) -> str:
        """Get the current active instructions.
        
        Returns:
            Current instructions string
        """
        return self.current_instructions
    
    def get_processor_status(self) -> dict:
        """Get the current status of the context switch processor.
        
        Returns:
            Dictionary containing processor status
        """
        current_planner = self.interview_context.get_current_planner_field()
        return {
            "type": "context_switch",
            "current_sequence": self.interview_context.current_workflow_step_sequence,
            "current_planner_id": current_planner.question_id if current_planner else None,
            "phase_transition_count": self.phase_transition_count,
            "current_instructions_length": len(self.current_instructions),
            "total_planner_fields": len(self.interview_context.planner_fields)
        }
    
    def _create_transition_message(self, instructions: str, planner_field: PlannerField) -> str:
        """Create a transition message for phase change.
        
        Args:
            instructions: The new instructions to inject
            planner_field: The planner field being transitioned to
            
        Returns:
            Formatted transition message
        """
        transition_message = f"""
--- INTERVIEW PHASE TRANSITION ---

You are now entering Phase {planner_field.sequence + 1} of the interview.

Please smoothly transition to this new phase while maintaining the conversational flow. 
Acknowledge the phase change naturally and begin following the new instructions.

Duration: {planner_field.duration} minutes
Focus Area: Question ID {planner_field.question_id}

New Instructions:

{instructions}

--- END PHASE TRANSITION ---
"""
        return transition_message
    
    def _create_closure_message(self, closure_instructions: str) -> str:
        """Create a closure message for interview end.
        
        Args:
            closure_instructions: The closure instructions
            
        Returns:
            Formatted closure message
        """
        session_duration = self.interview_context.get_session_duration()
        
        closure_message = f"""
--- INTERVIEW COMPLETION ---

The interview has completed all planned phases ({self.phase_transition_count} transitions).
Total session duration: {session_duration // 60} minutes and {session_duration % 60} seconds.

Closure Instructions:
{closure_instructions}

Please provide a natural conclusion to the interview, thank the candidate, and provide any final feedback or next steps as appropriate.

--- END INTERVIEW ---
"""
        return closure_message
    
    def _create_llm_context_frame(self, message: str) -> LLMMessagesUpdateFrame:
        """Create an LLM context frame with the given message.
        
        Args:
            message: The message to include in the context frame
            
        Returns:
            LLMMessagesUpdateFrame for injection into the pipeline
        """
        try:
            # Try Google-specific message format first
            from pipecat.services.google.llm import GoogleLLMContextMessage
            
            # Create a system message for context injection using Google message format
            system_message = GoogleLLMContextMessage(
                role="system",
                content=message
            )
            
            return LLMMessagesUpdateFrame(messages=[system_message], run_llm=True)
            
        except ImportError:
            try:
                # Fallback to OpenAI format
                from pipecat.services.openai import OpenAILLMContextMessage
                
                system_message = OpenAILLMContextMessage(
                    role="system",
                    content=message
                )
                
                return LLMMessagesUpdateFrame(messages=[system_message], run_llm=True)
                
            except ImportError:
                # Final fallback to simple dict format
                self.logger.warning("Using fallback dict message format for LLM context")
                messages = [
                    {
                        "role": "system", 
                        "content": message
                    }
                ]
                return LLMMessagesUpdateFrame(messages=messages, run_llm=True)
    
    def _get_default_instructions(self) -> str:
        """Get default instructions when planner field instructions are empty.
        
        Returns:
            Default instruction string
        """
        return """
Continue with the interview following standard professional practices. 
Ask relevant questions, evaluate responses, and maintain an engaging conversation.
Focus on assessing the candidate's technical skills and problem-solving abilities.
"""
    
    def _get_interview_closure_instructions(self) -> str:
        """Get instructions for interview closure.
        
        Returns:
            Closure instruction string
        """
        return """
The interview session is now complete. Please:

1. Thank the candidate for their time and participation
2. Provide brief, constructive feedback on their performance
3. Explain the next steps in the interview process
4. Ask if they have any final questions
5. End the session professionally

Be encouraging and positive while maintaining professionalism.
"""
