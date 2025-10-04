"""
InterviewTimerMonitor for managing interview phase timers and coordinating with ContextSwitchProcessor.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Callable, List
from app.entities.interview_context import InterviewContext, PlannerField
from app.entities.task_event import TaskEvent, TaskProperties
from app.models.enums import EventType, WorkflowStepType, ToolName
import structlog

logger = structlog.get_logger()


class InterviewTimerMonitor:
    """Monitor that manages timers and coordinates with ContextSwitchProcessor for interview phase transitions."""
    
    def __init__(self, interview_context: InterviewContext, context_processor=None, 
                 timer_callback: Optional[Callable] = None):
        """Initialize InterviewTimerMonitor.
        
        Args:
            interview_context: The interview context containing planner fields
            context_processor: The ContextSwitchProcessor for instruction management
            timer_callback: Optional callback function for timer events
        """
        self.interview_context = interview_context
        self.context_processor = context_processor
        self.timer_callback = timer_callback
        
        # Timer state
        self.current_timer_task: Optional[asyncio.Task] = None
        self.monitor_task: Optional[asyncio.Task] = None
        self.is_running = False
        self.is_paused = False
        self.start_time: Optional[datetime] = None
        self.pause_time: Optional[datetime] = None
        self.total_paused_duration = 0  # seconds
        
        # Current planner tracking
        self.current_planner_duration = 0  # minutes
        self.transitions_completed = 0
        
        self.logger = logger.bind(
            mock_interview_id=interview_context.mock_interview_id,
            session_id=interview_context.session_id
        )
        
        self.logger.info("InterviewTimerMonitor initialized", 
                        total_planner_fields=len(interview_context.planner_fields))
    
    async def start_current_planner_timer(self) -> bool:
        """Start timer for the current planner field.
        
        Returns:
            True if timer started successfully, False otherwise
        """
        try:
            current_planner = self.interview_context.get_current_planner_field()
            if not current_planner:
                self.logger.warning("No current planner field to start timer")
                return False
            
            # Cancel existing timer if running
            await self.stop_current_timer()
            
            # Set up timer parameters
            self.current_planner_duration = current_planner.duration
            duration_seconds = current_planner.duration * 60  # Convert minutes to seconds
            
            # Start the timer task
            self.current_timer_task = asyncio.create_task(
                self._run_timer(duration_seconds, current_planner)
            )
            
            # Start monitoring task for status updates
            self.monitor_task = asyncio.create_task(self._run_monitor())
            
            # Update state
            self.start_time = datetime.utcnow()
            self.is_running = True
            self.is_paused = False
            self.total_paused_duration = 0
            
            self.logger.info("🚀 Started planner timer", 
                           sequence=current_planner.sequence,
                           duration_minutes=current_planner.duration,
                           question_id=current_planner.question_id,
                           expected_end_time=(self.start_time + timedelta(minutes=current_planner.duration)).isoformat())
            
            # Trigger callback if provided
            if self.timer_callback:
                await self.timer_callback("timer_started", {
                    "planner_field": current_planner,
                    "duration_minutes": current_planner.duration
                })
            
            # Send SSE notification for phase start
            task_event = self._create_task_event_from_planner(current_planner, "phase_started")

            await self._send_sse_notification(EventType.INTERVIEW, task_event)
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to start planner timer", error=str(e))
            return False
    
    async def stop_current_timer(self) -> bool:
        """Stop the current timer.
        
        Returns:
            True if timer stopped successfully, False otherwise
        """
        try:
            # Cancel timer task
            if self.current_timer_task and not self.current_timer_task.done():
                self.current_timer_task.cancel()
                try:
                    await self.current_timer_task
                except asyncio.CancelledError:
                    pass
            
            # Cancel monitor task
            if self.monitor_task and not self.monitor_task.done():
                self.monitor_task.cancel()
                try:
                    await self.monitor_task
                except asyncio.CancelledError:
                    pass
            
            # Update state
            self.is_running = False
            self.is_paused = False
            self.current_timer_task = None
            self.monitor_task = None
            
            self.logger.info("Stopped planner timer")
            
            # Trigger callback if provided
            if self.timer_callback:
                await self.timer_callback("timer_stopped", {})
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to stop timer", error=str(e))
            return False
    
    async def pause_timer(self) -> bool:
        """Pause the current timer.
        
        Returns:
            True if timer paused successfully, False otherwise
        """
        if not self.is_running or self.is_paused:
            return False
        
        try:
            self.is_paused = True
            self.pause_time = datetime.utcnow()
            
            self.logger.info("Timer paused")
            
            # Trigger callback if provided
            if self.timer_callback:
                await self.timer_callback("timer_paused", {})
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to pause timer", error=str(e))
            return False
    
    async def resume_timer(self) -> bool:
        """Resume the paused timer.
        
        Returns:
            True if timer resumed successfully, False otherwise
        """
        if not self.is_running or not self.is_paused:
            return False
        
        try:
            if self.pause_time:
                pause_duration = (datetime.utcnow() - self.pause_time).total_seconds()
                self.total_paused_duration += pause_duration
            
            self.is_paused = False
            self.pause_time = None
            
            self.logger.info("Timer resumed", 
                           total_paused_seconds=self.total_paused_duration)
            
            # Trigger callback if provided
            if self.timer_callback:
                await self.timer_callback("timer_resumed", {})
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to resume timer", error=str(e))
            return False
    
    def get_timer_status(self) -> dict:
        """Get the current timer status.
        
        Returns:
            Dictionary containing timer status information
        """
        current_planner = self.interview_context.get_current_planner_field()
        
        status = {
            "is_running": self.is_running,
            "is_paused": self.is_paused,
            "current_sequence": self.interview_context.current_workflow_step_sequence,
            "current_planner_id": current_planner.question_id if current_planner else None,
            "current_duration_minutes": self.current_planner_duration,
            "transitions_completed": self.transitions_completed,
            "total_planner_fields": len(self.interview_context.planner_fields),
            "remaining_time_seconds": 0,
            "elapsed_time_seconds": 0,
            "progress_percentage": 0.0
        }
        
        if self.is_running and self.start_time:
            # Calculate elapsed time
            current_time = datetime.utcnow()
            if self.is_paused and self.pause_time:
                elapsed = (self.pause_time - self.start_time).total_seconds()
            else:
                elapsed = (current_time - self.start_time).total_seconds()
            
            # Subtract paused duration
            elapsed -= self.total_paused_duration
            
            # Calculate remaining time
            total_duration = self.current_planner_duration * 60
            remaining = max(0, total_duration - elapsed)
            
            # Calculate progress
            progress = min(100.0, (elapsed / total_duration) * 100) if total_duration > 0 else 0.0
            
            status.update({
                "remaining_time_seconds": int(remaining),
                "elapsed_time_seconds": int(elapsed),
                "progress_percentage": round(progress, 2)
            })
        
        return status
    
    def get_remaining_time_minutes(self) -> int:
        """Get remaining time in minutes.
        
        Returns:
            Remaining time in minutes
        """
        status = self.get_timer_status()
        return status["remaining_time_seconds"] // 60
    
    async def _run_timer(self, duration_seconds: int, planner_field: PlannerField):
        """Internal timer execution with pause support.
        
        Args:
            duration_seconds: Duration to run the timer
            planner_field: The planner field this timer is for
        """
        try:
            elapsed = 0
            check_interval = 1  # Check every second for pause state
            
            while elapsed < duration_seconds:
                await asyncio.sleep(check_interval)
                
                if not self.is_paused:
                    elapsed += check_interval
                
                # Check if we should continue
                if not self.is_running:
                    return
            
            # Timer completed
            await self.on_timer_expired()
            
        except asyncio.CancelledError:
            self.logger.info("Timer cancelled", 
                           sequence=planner_field.sequence,
                           elapsed_seconds=elapsed)
            raise
        except Exception as e:
            self.logger.error("Timer error", 
                            sequence=planner_field.sequence,
                            error=str(e))
    
    async def _run_monitor(self):
        """Internal monitoring task for periodic status updates."""
        try:
            update_count = 0
            while self.is_running:
                await asyncio.sleep(10)  # Update every 10 seconds (more frequent)
                if self.is_running:  # Check again after sleep
                    update_count += 1
                    status = self.get_timer_status()
                    
                    # Log INFO level every 30 seconds (every 3rd update), DEBUG level every 10 seconds
                    if update_count % 3 == 0:
                        self.logger.info("⏱️ Timer status update", 
                                       remaining_minutes=status["remaining_time_seconds"] // 60,
                                       progress_percent=status["progress_percentage"],
                                       current_sequence=status["current_sequence"],
                                       is_paused=status["is_paused"])
                    else:
                        self.logger.debug("Timer status update", **status)
                    
        except asyncio.CancelledError:
            self.logger.debug("Monitor task cancelled")
        except Exception as e:
            self.logger.error("Monitor task error", error=str(e))
    
    async def on_timer_expired(self):
        """Handle timer expiration and transition to next planner."""
        try:
            current_planner = self.interview_context.get_current_planner_field()
            
            self.logger.info("⏰ Timer expired, transitioning to next planner", 
                           current_sequence=self.interview_context.current_workflow_step_sequence,
                           current_planner_id=current_planner.question_id if current_planner else None,
                           completion_time=datetime.utcnow().isoformat())
            
            # Trigger callback if provided
            if self.timer_callback:
                await self.timer_callback("timer_expired", {
                    "completed_planner": current_planner
                })
            
            await self.transition_to_next_planner()
            
        except Exception as e:
            self.logger.error("Failed to handle timer expiration", error=str(e))
    
    async def transition_to_next_planner(self):
        """Transition to the next planner field or finalize interview."""
        try:
            # Check if there's a next planner field available before incrementing sequence
            current_sequence = self.interview_context.current_workflow_step_sequence
            next_sequence = current_sequence + 1
            
            # Check if next planner exists
            next_planner = None
            for planner_field in self.interview_context.planner_fields:
                if planner_field.sequence == next_sequence:
                    next_planner = planner_field
                    break
            
            if next_planner:
                # Move to next sequence only if next planner exists
                self.interview_context.move_to_next_sequence()
                self.transitions_completed += 1
                
                # Continue with next planner
                self.logger.info("🔄 Transitioning to next planner", 
                               new_sequence=next_planner.sequence,
                               question_id=next_planner.question_id,
                               duration_minutes=next_planner.duration,
                               transition_number=self.transitions_completed)
                
                # Inject new instructions if context processor is available
                if self.context_processor:
                    await self.context_processor.inject_planner_instructions(next_planner)
                
                # Start new timer
                await self.start_current_planner_timer()
                
                # Trigger callback if provided
                if self.timer_callback:
                    await self.timer_callback("planner_transitioned", {
                        "new_planner": next_planner,
                        "transition_count": self.transitions_completed
                    })
                
                # Send SSE notification for phase change
                task_event = self._create_task_event_from_planner(next_planner, "phase_changed")
  
                await self._send_sse_notification(EventType.INTERVIEW, task_event)
            else:
                # No more planners - finalize interview
                self.logger.info("🏁 No more planner fields available, finalizing interview", 
                               current_sequence=current_sequence,
                               total_planner_fields=len(self.interview_context.planner_fields))
                await self.finalize_interview()
                
        except Exception as e:
            self.logger.error("Failed to transition to next planner", error=str(e))
    
    async def finalize_interview(self):
        """Finalize the interview when all planners are complete."""
        try:
            self.is_running = False
            
            # Inject closure context if processor is available
            if self.context_processor:
                await self.context_processor.inject_interview_closure_context()
            
            session_duration = self.interview_context.get_session_duration()
            
            self.logger.info("🏁 Interview finalized - all planner fields completed", 
                           total_transitions=self.transitions_completed,
                           session_duration_seconds=session_duration,
                           session_duration_minutes=session_duration // 60,
                           total_planner_fields=len(self.interview_context.planner_fields),
                           finalization_time=datetime.utcnow().isoformat())
            
            # Trigger callback if provided
            if self.timer_callback:
                await self.timer_callback("interview_finalized", {
                    "total_transitions": self.transitions_completed,
                    "session_duration_seconds": session_duration
                })
            
            # Send SSE notification for interview completion
            # For system events like interview completion, create a minimal TaskEvent
            completion_task_event = TaskEvent(
                task_type=WorkflowStepType.WRAP_UP,
                tool_name=[],
                task_definition="Interview completed",
                task_properties=TaskProperties()
            )

            await self._send_sse_notification(EventType.SYSTEM, completion_task_event)
                
        except Exception as e:
            self.logger.error("Failed to finalize interview", error=str(e))
    
    def _infer_workflow_step_type_from_tools(self, tool_names: List[ToolName]) -> WorkflowStepType:
        """Infer WorkflowStepType based on the tools required."""
        if not tool_names:
            return WorkflowStepType.BEHAVIORAL
        
        # Check for specific tool combinations
        tool_values = [tool.value for tool in tool_names]
        
        if ToolName.CODE_EDITOR.value in tool_values:
            return WorkflowStepType.CODING
        elif ToolName.DESIGN_EDITOR.value in tool_values:
            return WorkflowStepType.SYSTEM_DESIGN
        else:
            return WorkflowStepType.BEHAVIORAL

    def _create_task_event_from_planner(self, planner_field: PlannerField, event_name: str) -> TaskEvent:
        """Create a TaskEvent from a planner field for SSE notifications."""
        # Infer WorkflowStepType from the tools required
        task_type = self._infer_workflow_step_type_from_tools(planner_field.tool_name or [])
        
        # Create task properties with question ID
        task_properties = TaskProperties(question_id=planner_field.question_id)
        
        # Create TaskEvent
        task_event = TaskEvent(
            task_type=task_type,
            tool_name=planner_field.tool_name or [],
            task_definition=planner_field.question_text,
            task_properties=task_properties
        )
        
        return task_event

    async def _send_sse_notification(self, event_type: EventType, task_event: TaskEvent):
        """Send SSE notification to connected clients using TaskEvent entity."""
        try:
            # Get the interview bot instance through the callback
            # This assumes the timer_callback has access to the bot instance
            if hasattr(self, '_bot_instance_ref'):
                bot_instance = self._bot_instance_ref()
                if bot_instance and hasattr(bot_instance, 'sse_connections'):
                    # Convert TaskEvent to dictionary and merge with additional data
                    task_data = task_event.to_dict()
                    
                    event_data = {
                        'event_type': event_type.value,
                        'data': task_data
                    }
                    
                    # Send to all SSE connections
                    for connection_queue in list(bot_instance.sse_connections):
                        try:
                            await connection_queue.put(event_data)
                        except Exception as e:
                            self.logger.warning("Failed to send SSE notification to connection", 
                                              event_type=event_type.value, error=str(e))
                            # Remove broken connection
                            bot_instance.sse_connections.discard(connection_queue)
                    
                    self.logger.debug("Sent SSE notification", 
                                    event_type=event_type.value,
                                    connections_count=len(bot_instance.sse_connections))
                    
        except Exception as e:
            self.logger.error("Error sending SSE notification", 
                            event_type=event_type.value, error=str(e))
    
    def set_bot_instance_reference(self, bot_instance_ref):
        """Set a weak reference to the bot instance for SSE notifications."""
        import weakref
        self._bot_instance_ref = weakref.ref(bot_instance_ref)

