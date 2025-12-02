from typing import List
from app.core.database import get_db_session
from app.dao.candidate_interview_dao import candidate_interview_dao
from app.models.candidate_interview import (
    CandidateInterviewRead
)

from app.models.enums import CandidateInterviewStatus
import structlog

logger = structlog.get_logger()


class CandidateInterviewService:
    """Service layer for candidate interview operations"""
    
    async def create_candidate_interview(self, interview_data: dict, user_id: str) -> CandidateInterviewRead:
        """Create a new candidate interview"""
        db = await get_db_session()
        try:
            # Add user_id to interview data
            interview_data["userId"] = user_id
            
            # Create the interview
            created_interview = await candidate_interview_dao.create(db, obj_in=interview_data)
            
            logger.info("Created candidate interview", 
                       interview_id=str(created_interview.id), 
                       user_id=user_id)
            
            return CandidateInterviewRead.from_orm(created_interview)
            
        except Exception as e:
            logger.error("Failed to create candidate interview", error=str(e))
            raise
        finally:
            await db.close()

    async def get_user_interviews(self, user_id: str, skip: int = 0, limit: int = 100) -> List[CandidateInterviewRead]:
        """Get all interviews for a specific user"""
        db = await get_db_session()
        try:
            interviews = await candidate_interview_dao.get_by_user_id(db, user_id)
            
            # Apply pagination
            paginated_interviews = interviews[skip:skip + limit]
            
            return [CandidateInterviewRead.from_orm(interview) for interview in paginated_interviews]
            
        except Exception as e:
            logger.error("Failed to get user interviews", error=str(e))
            raise
        finally:
            await db.close()

    async def get_candidate_interview(self, interview_id: str, user_id: str) -> CandidateInterviewRead:
        """Get a specific candidate interview by ID"""
        db = await get_db_session()
        try:
            interview = await candidate_interview_dao.get_by_id(db, interview_id)
            if not interview:
                raise ValueError("Candidate interview not found")
            
            # Verify ownership
            if interview.userId != user_id:
                raise ValueError("Not authorized to access this interview")
            
            return CandidateInterviewRead.from_orm(interview)
            
        except Exception as e:
            logger.error("Failed to get candidate interview", interview_id=interview_id, error=str(e))
            raise
        finally:
            await db.close()

    async def update_candidate_interview(self, interview_id: str, update_data: dict, user_id: str) -> CandidateInterviewRead:
        """Update a candidate interview"""
        db = await get_db_session()
        try:
            # Get existing interview
            existing_interview = await candidate_interview_dao.get_by_id(db, interview_id)
            if not existing_interview:
                raise ValueError("Candidate interview not found")
            
            # Verify ownership
            if existing_interview.userId != user_id:
                raise ValueError("Not authorized to update this interview")
            
            # Update the interview
            updated_interview = await candidate_interview_dao.update(
                db, db_obj=existing_interview, obj_in=update_data
            )
            
            logger.info("Updated candidate interview", interview_id=interview_id, user_id=user_id)
            return CandidateInterviewRead.from_orm(updated_interview)
            
        except Exception as e:
            logger.error("Failed to update candidate interview", interview_id=interview_id, error=str(e))
            raise
        finally:
            await db.close()

    async def update_interview_status(self, interview_id: str, status: CandidateInterviewStatus, user_id: str) -> dict:
        """Update the status of a candidate interview"""
        db = await get_db_session()
        try:
            # Get existing interview
            existing_interview = await candidate_interview_dao.get_by_id(db, interview_id)
            if not existing_interview:
                raise ValueError("Candidate interview not found")
            
            # Verify ownership
            if existing_interview.userId != user_id:
                raise ValueError("Not authorized to update this interview")
            
            # Update status
            updated_interview = await candidate_interview_dao.update_status(db, interview_id, status)
            
            logger.info("Updated interview status", interview_id=interview_id, status=status, user_id=user_id)
            return {"message": "Interview status updated successfully", "status": status}
            
        except Exception as e:
            logger.error("Failed to update interview status", interview_id=interview_id, error=str(e))
            raise
        finally:
            await db.close()

    async def delete_candidate_interview(self, interview_id: str, user_id: str) -> dict:
        """Delete a candidate interview"""
        db = await get_db_session()
        try:
            # Get existing interview
            existing_interview = await candidate_interview_dao.get_by_id(db, interview_id)
            if not existing_interview:
                raise ValueError("Candidate interview not found")
            
            # Verify ownership
            if existing_interview.userId != user_id:
                raise ValueError("Not authorized to delete this interview")
            
            # Delete the interview
            await candidate_interview_dao.delete(db, id=interview_id)
            
            logger.info("Deleted candidate interview", interview_id=interview_id, user_id=user_id)
            return {"message": "Interview deleted successfully"}
            
        except Exception as e:
            logger.error("Failed to delete candidate interview", interview_id=interview_id, error=str(e))
            raise
        finally:
            await db.close()

    async def get_interviews_by_status(self, user_id: str, status: CandidateInterviewStatus) -> List[CandidateInterviewRead]:
        """Get interviews for a specific user with a specific status"""
        db = await get_db_session()
        try:
            interviews = await candidate_interview_dao.get_user_interviews_by_status(db, user_id, status)
            return [CandidateInterviewRead.from_orm(interview) for interview in interviews]
            
        except Exception as e:
            logger.error("Failed to get interviews by status", user_id=user_id, status=status, error=str(e))
            raise
        finally:
            await db.close()

    async def get_active_interviews(self) -> List[CandidateInterviewRead]:
        """Get all interviews that are currently in progress"""
        db = await get_db_session()
        try:
            interviews = await candidate_interview_dao.get_active_interviews(db)
            return [CandidateInterviewRead.from_orm(interview) for interview in interviews]
            
        except Exception as e:
            logger.error("Failed to get active interviews", error=str(e))
            raise
        finally:
            await db.close()

    async def get_completed_interviews(self) -> List[CandidateInterviewRead]:
        """Get all completed interviews"""
        db = await get_db_session()
        try:
            interviews = await candidate_interview_dao.get_completed_interviews(db)
            return [CandidateInterviewRead.from_orm(interview) for interview in interviews]
            
        except Exception as e:
            logger.error("Failed to get completed interviews", error=str(e))
            raise
        finally:
            await db.close()

    async def validate_interview_ownership(self, interview_id: str, user_id: str) -> None:
        """
        Validate that an interview exists and belongs to the specified user.
        Raises ValueError if validation fails.
        
        Args:
            interview_id: The candidate interview ID to validate
            user_id: The user ID to validate ownership against
            
        Raises:
            ValueError: If interview not found or user doesn't own it
        """
        db = await get_db_session()
        try:
            interview = await candidate_interview_dao.get_by_id(db, interview_id)
            if not interview:
                logger.warning("Interview not found", interview_id=interview_id, user_id=user_id)
                raise ValueError("Candidate interview not found")
            
            if interview.userId != user_id:
                logger.warning("Interview ownership validation failed", 
                             interview_id=interview_id, 
                             expected_user_id=user_id,
                             actual_user_id=interview.userId)
                raise ValueError("Not authorized to access this interview")
            
            logger.debug("Interview ownership validated successfully", 
                        interview_id=interview_id, 
                        user_id=user_id)
            
        except ValueError:
            raise
        except Exception as e:
            logger.error("Failed to validate interview ownership", 
                        interview_id=interview_id, 
                        user_id=user_id, 
                        error=str(e))
            raise
        finally:
            await db.close()


# Create a singleton instance
candidate_interview_service = CandidateInterviewService()
