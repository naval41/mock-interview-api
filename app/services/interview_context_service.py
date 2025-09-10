"""
InterviewContext service for building and managing interview context objects.
This service handles the creation of InterviewContext entities from database data.
"""

from typing import Optional
from datetime import time
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.core.database import get_db_session
from app.dao.candidate_interview_dao import candidate_interview_dao
from app.dao.candidate_interview_planner_dao import candidate_interview_planner_dao
from app.entities.interview_context import InterviewContext, PlannerField
from app.models.workflow import WorkflowStep
import structlog
import uuid

logger = structlog.get_logger()


class InterviewContextService:
    """Service layer for interview context operations"""
    
    async def build_interview_context(
        self, 
        mock_interview_id: str, 
        user_id: str, 
        session_id: Optional[str] = None
    ) -> InterviewContext:
        """
        Build an InterviewContext object from mock_interview_id and user_id.
        
        Args:
            mock_interview_id: The mock interview identifier
            user_id: The user identifier
            session_id: Optional session ID (will generate if not provided)
            
        Returns:
            InterviewContext: The built interview context object
            
        Raises:
            ValueError: If mock interview not found or user not authorized
        """
        db = await get_db_session()
        try:
            # Generate session_id if not provided
            if not session_id:
                session_id = str(uuid.uuid4())
            
            logger.info("Building interview context", 
                       mock_interview_id=mock_interview_id, 
                       user_id=user_id, 
                       session_id=session_id)
            
            # Step 1: Find the candidate interview by mock_interview_id and user_id
            candidate_interview = await self._find_candidate_interview(
                db, mock_interview_id, user_id
            )
            
            # Step 2: Get all interview planners ordered by sequence
            interview_planners = await self._get_all_interview_planners_ordered(
                db, candidate_interview.id
            )
            
            if not interview_planners:
                raise ValueError(f"No interview planners found for candidate interview: {candidate_interview.id}")
            
            # Step 3: Create planner fields from planners (with duration from WorkflowStep)
            planner_fields = []
            for planner in interview_planners:
                # Get duration from the related WorkflowStep
                duration = await self._get_workflow_step_duration(db, planner.workflowStepId)
                
                planner_field = PlannerField(
                    question_id=planner.questionId,
                    knowledge_bank_id=planner.knowledgeBankId,
                    interview_instructions=planner.interviewInstructions,
                    duration=duration,
                    sequence=planner.sequence
                    # start_time and end_time will be set separately when needed
                )
                planner_fields.append(planner_field)
            
            # Step 4: Build the InterviewContext with planner fields
            first_planner = interview_planners[0]  # First in sequence
            interview_context = InterviewContext(
                mock_interview_id=mock_interview_id,
                user_id=user_id,
                session_id=session_id,
                interview_planner_id=first_planner.id,
                current_workflow_step_sequence=0,  # Start at sequence 0
                current_question_id=first_planner.questionId,
                current_workflow_step_id=first_planner.workflowStepId,
                planner_fields=planner_fields
            )
            
            logger.info("Successfully built interview context", 
                       context_id=str(interview_context),
                       interview_planner_id=first_planner.id,
                       question_id=first_planner.questionId,
                       workflow_step_id=first_planner.workflowStepId,
                       planner_fields_count=len(planner_fields))
            
            return interview_context
            
        except Exception as e:
            logger.error("Failed to build interview context", 
                        mock_interview_id=mock_interview_id, 
                        user_id=user_id, 
                        error=str(e))
            raise
        finally:
            await db.close()
    
    async def _find_candidate_interview(
        self, 
        db: AsyncSession, 
        mock_interview_id: str, 
        user_id: str
    ):
        """Find candidate interview by mock_interview_id and user_id"""
        try:
            # Use the DAO method to find the candidate interview
            candidate_interview = await candidate_interview_dao.get_by_mock_interview_and_user(
                db, mock_interview_id, user_id
            )
            
            if not candidate_interview:
                raise ValueError(f"Mock interview not found for mock_interview_id: {mock_interview_id} and user_id: {user_id}")
            
            logger.info("Found candidate interview", 
                       interview_id=candidate_interview.id,
                       mock_interview_id=mock_interview_id,
                       user_id=user_id)
            
            return candidate_interview
            
        except Exception as e:
            logger.error("Error finding candidate interview", 
                        mock_interview_id=mock_interview_id, 
                        user_id=user_id, 
                        error=str(e))
            raise
    
    async def _get_all_interview_planners_ordered(
        self, 
        db: AsyncSession, 
        candidate_interview_id: str
    ):
        """Get all interview planners for a candidate interview, ordered by sequence ASC"""
        try:
            # Get all planners for the candidate interview
            planners = await candidate_interview_planner_dao.get_interview_plan(
                db, candidate_interview_id
            )
            
            if not planners:
                raise ValueError(f"No interview planners found for candidate interview: {candidate_interview_id}")
            
            # Sort by sequence (ascending) and then by creation time
            sorted_planners = sorted(planners, key=lambda p: (p.sequence, p.createdAt))
            
            logger.info("Found interview planners", 
                       candidate_interview_id=candidate_interview_id,
                       planners_count=len(sorted_planners),
                       sequences=[p.sequence for p in sorted_planners])
            
            return sorted_planners
            
        except Exception as e:
            logger.error("Error getting interview planners", 
                        candidate_interview_id=candidate_interview_id, 
                        error=str(e))
            raise
    
    async def update_interview_context_sequence(
        self, 
        interview_context: InterviewContext, 
        new_sequence: int
    ) -> InterviewContext:
        """
        Update the workflow step sequence in an interview context.
        
        Args:
            interview_context: The current interview context
            new_sequence: The new sequence number
            
        Returns:
            InterviewContext: Updated interview context
        """
        try:
            interview_context.update_workflow_step_sequence(new_sequence)
            
            logger.info("Updated interview context sequence", 
                       mock_interview_id=interview_context.mock_interview_id,
                       old_sequence=interview_context.current_workflow_step_sequence - 1,
                       new_sequence=new_sequence)
            
            return interview_context
            
        except Exception as e:
            logger.error("Failed to update interview context sequence", 
                        mock_interview_id=interview_context.mock_interview_id,
                        sequence=new_sequence,
                        error=str(e))
            raise
    
    async def move_to_next_sequence(self, interview_context: InterviewContext) -> InterviewContext:
        """
        Move the interview context to the next sequence.
        
        Args:
            interview_context: The current interview context
            
        Returns:
            InterviewContext: Updated interview context
        """
        try:
            interview_context.move_to_next_sequence()
            
            logger.info("Moved to next sequence", 
                       mock_interview_id=interview_context.mock_interview_id,
                       new_sequence=interview_context.current_workflow_step_sequence)
            
            return interview_context
            
        except Exception as e:
            logger.error("Failed to move to next sequence", 
                        mock_interview_id=interview_context.mock_interview_id,
                        error=str(e))
            raise
    
    async def update_planner_field_timing(
        self, 
        interview_context: InterviewContext, 
        sequence: int, 
        start_time: Optional[time] = None, 
        end_time: Optional[time] = None
    ) -> InterviewContext:
        """
        Update the timing for a specific planner field.
        
        Args:
            interview_context: The current interview context
            sequence: The sequence number of the planner field to update
            start_time: Optional start time for the planner field
            end_time: Optional end time for the planner field
            
        Returns:
            InterviewContext: Updated interview context
        """
        try:
            # Find the planner field with the matching sequence
            for planner_field in interview_context.planner_fields:
                if planner_field.sequence == sequence:
                    if start_time is not None:
                        planner_field.start_time = start_time
                    if end_time is not None:
                        planner_field.end_time = end_time
                    
                    logger.info("Updated planner field timing", 
                               mock_interview_id=interview_context.mock_interview_id,
                               sequence=sequence,
                               start_time=start_time,
                               end_time=end_time)
                    break
            else:
                logger.warning("Planner field not found for sequence", 
                              mock_interview_id=interview_context.mock_interview_id,
                              sequence=sequence)
            
            return interview_context
            
        except Exception as e:
            logger.error("Failed to update planner field timing", 
                        mock_interview_id=interview_context.mock_interview_id,
                        sequence=sequence,
                        error=str(e))
            raise
    
    async def _get_workflow_step_duration(
        self, 
        db: AsyncSession, 
        workflow_step_id: str
    ) -> int:
        """Get the duration from WorkflowStep for a given workflow step ID"""
        try:
            result = await db.execute(
                select(WorkflowStep).where(WorkflowStep.id == workflow_step_id)
            )
            workflow_step = result.scalar_one_or_none()
            
            if not workflow_step:
                logger.warning("WorkflowStep not found, using default duration", 
                              workflow_step_id=workflow_step_id)
                return 30  # Default 30 minutes if not found
            
            logger.debug("Retrieved workflow step duration", 
                        workflow_step_id=workflow_step_id,
                        duration=workflow_step.duration)
            
            return workflow_step.duration
            
        except Exception as e:
            logger.error("Error getting workflow step duration", 
                        workflow_step_id=workflow_step_id, 
                        error=str(e))
            # Return default duration on error
            return 30


# Create a singleton instance
interview_context_service = InterviewContextService()
