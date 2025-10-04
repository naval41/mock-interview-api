"""
ContextSwitchProcessor for managing LLM instruction transitions during interview phases.
"""

from datetime import datetime
from pipecat.frames.frames import BotInterruptionFrame, ControlFrame, Frame, LLMMessagesAppendFrame, LLMTextFrame, InterruptionTaskFrame
from app.interview_playground.frames.interview_frames import InterviewClosureFrame
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
        self._interview_completed = False
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
            # Check if interview is already completed
            if self._interview_completed:
                self.logger.warning("Attempted to inject planner instructions after interview completion - ignoring", 
                                  sequence=planner_field.sequence,
                                  question_id=planner_field.question_id)
                return False
            
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
            
            # Then, create and send the closure message
            context_frame = self._create_llm_context_frame_for_bot_interruption(closure_message)
            await self.push_frame(context_frame, FrameDirection.DOWNSTREAM)
            
            self.current_instructions = closure_instructions
            
            # Mark interview as completed to prevent further context injections
            self._interview_completed = True
            
            self.logger.info("Injected interview closure context with bot interruption", 
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

The interview session has now concluded. This is the FINAL message you should deliver.

Session Duration: {session_duration} seconds ({session_duration // 60} minutes)
Total Phases Completed: {self.phase_transition_count + 1}

IMPORTANT: After delivering this closing message, the interview is officially over. 
Do not continue with any new problems, questions, or technical discussions.

{closure_instructions}

--- END INTERVIEW ---
"""
        return closure_message
    
    def _create_llm_context_frame(self, message: str) -> LLMMessagesAppendFrame:
        """Create an LLM context frame with the given message.
        
        Args:
            message: The message to include in the context frame
            
        Returns:
            LLMMessagesUpdateFrame for injection into the pipeline
        """
        # Use standard dict format for LLM messages
        self.logger.debug("Creating LLM context message with dict format")
        messages = [
            {
                "role": "system", 
                "content": message
            }
        ]
        return LLMMessagesAppendFrame(messages=messages, run_llm=True)
    
    def _create_llm_context_frame_for_bot_interruption(self, message: str) -> InterviewClosureFrame:
        """Create InterviewClosureFrame for interview closure.
        
        Args:
            message: The message to include in the closure frame
            
        Returns:
            InterviewClosureFrame for injection into the pipeline
        """
        session_duration = self.interview_context.get_session_duration()
        self.logger.debug("Creating InterviewClosureFrame for interview closure", 
                         message_length=len(message),
                         session_duration=session_duration)
        
        return InterviewClosureFrame(
            message=message,
            session_duration=session_duration,
            completion_reason="timer_expired"
        )
    
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
You are now concluding a mock interview session. This is your FINAL response - the interview is officially over.

<CRITICAL_INSTRUCTIONS>
1. This is the LAST message you will deliver in this interview
2. After this message, the interview session ends completely
3. Do NOT continue with any new problems, questions, or technical discussions
4. Do NOT ask if the candidate has questions about the problems
5. Do NOT provide additional coding challenges or explanations
6. The interview timer has expired and the session is concluded
</CRITICAL_INSTRUCTIONS>

<What_to_include_in_your_closing_message>
1. Clearly state that the interview session has concluded
2. Thank the candidate sincerely for their time and participation
3. Acknowledge their effort and engagement throughout the session
4. Provide encouragement about their problem-solving approach
5. Mention that they will receive feedback on their performance
6. Wish them well in their continued preparation
7. End with a warm, professional closing
</What_to_include_in_your_closing_message>

<Tone_and_Style>
1. Warm, professional, and encouraging
2. Conversational and natural (not robotic)
3. Comprehensive but concise (aim for 1-2 minutes of speaking time)
4. Confident and supportive
5. Clear that this is the end of the session
</Tone_and_Style>

<Example_Structure>
"Excellent work today! We've reached the end of our interview session, and I want to thank you for your time and thoughtful participation. Your approach to problem-solving shows strong analytical thinking, and I appreciate how you worked through the challenges we discussed. You'll receive detailed feedback on your performance, including areas of strength and opportunities for growth. Keep practicing and building on what you've learned today. Best of luck with your continued preparation, and thank you again for a great session!"
</Example_Structure>

REMEMBER: This is your final message. After speaking this, the interview is completely finished.
        """
