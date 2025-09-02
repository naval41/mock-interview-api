from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db_session
from app.dao.candidate_interview_planner_dao import candidate_interview_planner_dao
from app.dao.candidate_interview_dao import candidate_interview_dao
from app.models.candidate_interview_planner import (
    CandidateInterviewPlanner, 
    CandidateInterviewPlannerCreate, 
    CandidateInterviewPlannerRead, 
    CandidateInterviewPlannerUpdate
)
import structlog

logger = structlog.get_logger()


class CandidateInterviewPlannerService:
    """Service layer for candidate interview planner operations"""
    
    async def create_interview_planner(self, planner_data: dict, user_id: str) -> CandidateInterviewPlannerRead:
        """Create a new interview planner entry"""
        db = await get_db_session()
        try:
            # Verify the candidate interview exists and belongs to the user
            candidate_interview = await candidate_interview_dao.get_by_id(db, planner_data["candidateInterviewId"])
            if not candidate_interview:
                raise ValueError("Candidate interview not found")
            
            if candidate_interview.userId != user_id:
                raise ValueError("Not authorized to create planner for this interview")
            
            # Create the planner
            created_planner = await candidate_interview_planner_dao.create(db, obj_in=planner_data)
            
            logger.info("Created interview planner", 
                       planner_id=str(created_planner.id), 
                       interview_id=planner_data["candidateInterviewId"],
                       user_id=user_id)
            
            return CandidateInterviewPlannerRead.from_orm(created_planner)
            
        except Exception as e:
            logger.error("Failed to create interview planner", error=str(e))
            raise
        finally:
            await db.close()

    async def get_interview_plan(self, interview_id: str, user_id: str) -> List[CandidateInterviewPlannerRead]:
        """Get the complete interview plan for a candidate interview"""
        db = await get_db_session()
        try:
            # Verify the candidate interview exists and belongs to the user
            candidate_interview = await candidate_interview_dao.get_by_id(db, interview_id)
            if not candidate_interview:
                raise ValueError("Candidate interview not found")
            
            if candidate_interview.userId != user_id:
                raise ValueError("Not authorized to access this interview plan")
            
            # Get the interview plan
            plan = await candidate_interview_planner_dao.get_interview_plan(db, interview_id)
            
            return [CandidateInterviewPlannerRead.from_orm(planner) for planner in plan]
            
        except Exception as e:
            logger.error("Failed to get interview plan", interview_id=interview_id, error=str(e))
            raise
        finally:
            await db.close()

    async def get_interview_planner(self, planner_id: str, user_id: str) -> CandidateInterviewPlannerRead:
        """Get a specific interview planner by ID"""
        db = await get_db_session()
        try:
            planner = await candidate_interview_planner_dao.get_by_id(db, planner_id)
            if not planner:
                raise ValueError("Interview planner not found")
            
            # Verify ownership through the candidate interview
            candidate_interview = await candidate_interview_dao.get_by_id(db, planner.candidateInterviewId)
            if candidate_interview.userId != user_id:
                raise ValueError("Not authorized to access this planner")
            
            return CandidateInterviewPlannerRead.from_orm(planner)
            
        except Exception as e:
            logger.error("Failed to get interview planner", planner_id=planner_id, error=str(e))
            raise
        finally:
            await db.close()

    async def update_interview_planner(self, planner_id: str, update_data: dict, user_id: str) -> CandidateInterviewPlannerRead:
        """Update an interview planner"""
        db = await get_db_session()
        try:
            # Get existing planner
            existing_planner = await candidate_interview_planner_dao.get_by_id(db, planner_id)
            if not existing_planner:
                raise ValueError("Interview planner not found")
            
            # Verify ownership through the candidate interview
            candidate_interview = await candidate_interview_dao.get_by_id(db, existing_planner.candidateInterviewId)
            if candidate_interview.userId != user_id:
                raise ValueError("Not authorized to update this planner")
            
            # Update the planner
            updated_planner = await candidate_interview_planner_dao.update(
                db, db_obj=existing_planner, obj_in=update_data
            )
            
            logger.info("Updated interview planner", planner_id=planner_id, user_id=user_id)
            return CandidateInterviewPlannerRead.from_orm(updated_planner)
            
        except Exception as e:
            logger.error("Failed to update interview planner", planner_id=planner_id, error=str(e))
            raise
        finally:
            await db.close()

    async def update_planner_instructions(self, planner_id: str, instructions: str, user_id: str) -> dict:
        """Update the interview instructions for a specific planner"""
        db = await get_db_session()
        try:
            # Get existing planner
            existing_planner = await candidate_interview_planner_dao.get_by_id(db, planner_id)
            if not existing_planner:
                raise ValueError("Interview planner not found")
            
            # Verify ownership through the candidate interview
            candidate_interview = await candidate_interview_dao.get_by_id(db, existing_planner.candidateInterviewId)
            if candidate_interview.userId != user_id:
                raise ValueError("Not authorized to update this planner")
            
            # Update instructions
            updated_planner = await candidate_interview_planner_dao.update_interview_instructions(
                db, planner_id, instructions
            )
            
            logger.info("Updated planner instructions", planner_id=planner_id, user_id=user_id)
            return {"message": "Instructions updated successfully", "instructions": instructions}
            
        except Exception as e:
            logger.error("Failed to update planner instructions", planner_id=planner_id, error=str(e))
            raise
        finally:
            await db.close()

    async def get_next_planner_in_sequence(self, planner_id: str, user_id: str) -> Optional[CandidateInterviewPlannerRead]:
        """Get the next planner in the interview sequence"""
        db = await get_db_session()
        try:
            # Get current planner
            current_planner = await candidate_interview_planner_dao.get_by_id(db, planner_id)
            if not current_planner:
                raise ValueError("Interview planner not found")
            
            # Verify ownership through the candidate interview
            candidate_interview = await candidate_interview_dao.get_by_id(db, current_planner.candidateInterviewId)
            if candidate_interview.userId != user_id:
                raise ValueError("Not authorized to access this planner")
            
            # Get next planner
            next_planner = await candidate_interview_planner_dao.get_next_planner_in_sequence(
                db, current_planner.candidateInterviewId, planner_id
            )
            
            if next_planner:
                return CandidateInterviewPlannerRead.from_orm(next_planner)
            else:
                return None
            
        except Exception as e:
            logger.error("Failed to get next planner", planner_id=planner_id, error=str(e))
            raise
        finally:
            await db.close()

    async def delete_interview_planner(self, planner_id: str, user_id: str) -> dict:
        """Delete an interview planner"""
        db = await get_db_session()
        try:
            # Get existing planner
            existing_planner = await candidate_interview_planner_dao.get_by_id(db, planner_id)
            if not existing_planner:
                raise ValueError("Interview planner not found")
            
            # Verify ownership through the candidate interview
            candidate_interview = await candidate_interview_dao.get_by_id(db, existing_planner.candidateInterviewId)
            if candidate_interview.userId != user_id:
                raise ValueError("Not authorized to delete this planner")
            
            # Delete the planner
            await candidate_interview_planner_dao.delete(db, id=planner_id)
            
            logger.info("Deleted interview planner", planner_id=planner_id, user_id=user_id)
            return {"message": "Interview planner deleted successfully"}
            
        except Exception as e:
            logger.error("Failed to delete interview planner", planner_id=planner_id, error=str(e))
            raise
        finally:
            await db.close()

    async def delete_interview_plan(self, interview_id: str, user_id: str) -> dict:
        """Delete the entire interview plan for a candidate interview"""
        db = await get_db_session()
        try:
            # Verify the candidate interview exists and belongs to the user
            candidate_interview = await candidate_interview_dao.get_by_id(db, interview_id)
            if not candidate_interview:
                raise ValueError("Candidate interview not found")
            
            if candidate_interview.userId != user_id:
                raise ValueError("Not authorized to delete this interview plan")
            
            # Delete the entire plan
            await candidate_interview_planner_dao.delete_interview_plan(db, interview_id)
            
            logger.info("Deleted interview plan", interview_id=interview_id, user_id=user_id)
            return {"message": "Interview plan deleted successfully"}
            
        except Exception as e:
            logger.error("Failed to delete interview plan", interview_id=interview_id, error=str(e))
            raise
        finally:
            await db.close()

    async def get_planners_by_criteria(
        self,
        user_id: str,
        candidate_interview_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        workflow_step_id: Optional[str] = None,
        question_id: Optional[str] = None,
        knowledge_bank_id: Optional[str] = None
    ) -> List[CandidateInterviewPlannerRead]:
        """Get planners based on multiple optional criteria"""
        db = await get_db_session()
        try:
            # If candidate_interview_id is provided, verify ownership
            if candidate_interview_id:
                candidate_interview = await candidate_interview_dao.get_by_id(db, candidate_interview_id)
                if not candidate_interview or candidate_interview.userId != user_id:
                    raise ValueError("Not authorized to access this interview")
            
            # Get planners by criteria
            planners = await candidate_interview_planner_dao.get_planners_by_multiple_criteria(
                db, candidate_interview_id, workflow_id, workflow_step_id, question_id, knowledge_bank_id
            )
            
            return [CandidateInterviewPlannerRead.from_orm(planner) for planner in planners]
            
        except Exception as e:
            logger.error("Failed to get planners by criteria", error=str(e))
            raise
        finally:
            await db.close()


# Create a singleton instance
candidate_interview_planner_service = CandidateInterviewPlannerService()
