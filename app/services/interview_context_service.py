"""
InterviewContext service for building and managing interview context objects.
This service handles the creation of InterviewContext entities from database data.
"""

from typing import Optional
from datetime import time
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db_session
from app.dao.candidate_interview_dao import candidate_interview_dao
from app.dao.candidate_interview_planner_dao import candidate_interview_planner_dao
from app.entities.interview_context import InterviewContext, PlannerField
from app.models.interview_question import InterviewQuestion
import structlog
import uuid

logger = structlog.get_logger()


class InterviewContextService:
    """Service layer for interview context operations"""
    
    async def build_interview_context(
        self, 
        candidate_interview_id: str, 
        user_id: str, 
        session_id: Optional[str] = None
    ) -> InterviewContext:
        """
        Build an InterviewContext object from mock_interview_id and user_id.
        
        Args:
            candidate_interview_id: The candidate interview identifier
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
                       candidate_interview_id=candidate_interview_id, 
                       user_id=user_id, 
                       session_id=session_id)
            
            # Step 1: Find the candidate interview by mock_interview_id and user_id
            candidate_interview = await self._find_candidate_interview(
                db, candidate_interview_id, user_id
            )
            
            # Step 2: Get all interview planners ordered by sequence
            interview_planners = await self._get_all_interview_planners_ordered(
                db, candidate_interview.id
            )
            
            if not interview_planners:
                raise ValueError(f"No interview planners found for candidate interview: {candidate_interview.id}")
            
            # Step 3: Fetch interview questions for all question IDs
            question_ids = [planner.questionId for planner in interview_planners]
            interview_questions = await self._fetch_interview_questions(db, question_ids)
            
            # Step 4: Create planner fields from planners (using duration directly from planner)
            planner_fields = []
            for planner in interview_planners:
                planner_field = PlannerField(
                    question_id=planner.questionId,
                    knowledge_bank_id=planner.knowledgeBankId,
                    interview_instructions=planner.interviewInstructions,
                    duration=planner.duration,  # Use duration directly from planner
                    sequence=planner.sequence
                    # start_time and end_time will be set separately when needed
                )
                # Set tool names directly from database toolName field
                planner_field.set_tools_from_string(planner.toolName)
                
                # Set question text from fetched interview questions
                if planner.questionId in interview_questions:
                    question = interview_questions[planner.questionId]
                    planner_field.set_question_text(question.question)
                    
                planner_fields.append(planner_field)
            
            # Step 5: Build the InterviewContext with planner fields
            first_planner = interview_planners[0]  # First in sequence
            
            # Start with the actual sequence of the first planner (might be 1, not 0)
            initial_sequence = first_planner.sequence
            
            interview_context = InterviewContext(
                mock_interview_id=candidate_interview_id,
                user_id=user_id,
                session_id=session_id,
                interview_planner_id=first_planner.id,
                candidate_interview_id=candidate_interview.id,  # Add the actual candidate interview ID
                current_workflow_step_sequence=initial_sequence,  # Use actual first sequence
                current_question_id=first_planner.questionId,
                current_workflow_step_id=first_planner.workflowStepId,
                planner_fields=planner_fields
            )
            
            logger.info("Successfully built interview context", 
                       context_id=str(interview_context),
                       candidate_interview_id=candidate_interview.id,
                       interview_planner_id=first_planner.id,
                       question_id=first_planner.questionId,
                       workflow_step_id=first_planner.workflowStepId,
                       initial_sequence=initial_sequence,
                       planner_fields_count=len(planner_fields),
                       total_duration_minutes=sum(pf.duration for pf in planner_fields),
                       planner_sequences=[pf.sequence for pf in planner_fields])
            
            return interview_context
            
        except Exception as e:
            logger.error("Failed to build interview context", 
                        candidate_interview_id=candidate_interview_id, 
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
    
    async def _fetch_interview_questions(
        self, 
        db: AsyncSession, 
        question_ids: list[str]
    ) -> dict[str, InterviewQuestion]:
        """
        Fetch interview questions by their IDs.
        
        Args:
            db: Database session
            question_ids: List of question IDs to fetch
            
        Returns:
            Dictionary with question_id as key and InterviewQuestion object as value
        """
        try:
            if not question_ids:
                return {}
            
            # Query interview questions by IDs
            questions = []
            for question_id in question_ids:
                stmt = select(InterviewQuestion).where(InterviewQuestion.id == question_id)
                result = await db.execute(stmt)
                question = result.scalar_one_or_none()
                if question:
                    questions.append(question)
            
            # Convert to dictionary for easy lookup
            questions_dict = {question.id: question for question in questions}
            
            logger.info("Fetched interview questions", 
                       requested_count=len(question_ids),
                       found_count=len(questions_dict),
                       question_ids=question_ids)
            
            return questions_dict
            
        except Exception as e:
            logger.error("Error fetching interview questions", 
                        question_ids=question_ids, 
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
    


# Create a singleton instance
interview_context_service = InterviewContextService()
