"""
Interview Completion Service for handling interview completion workflow.

This service orchestrates:
1. Validating interview state
2. Updating interview status in database
3. Sending SQS notification
4. Logging completion events
"""

from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db_session
from app.dao.candidate_interview_dao import candidate_interview_dao
from app.services.sqs_service import sqs_service
from app.models.enums import CandidateInterviewStatus, CompletionReason
from app.models.candidate_interview import CandidateInterview
import structlog

logger = structlog.get_logger()


class InterviewCompletionService:
    """Service for handling interview completion workflow."""
    
    def __init__(self):
        """Initialize Interview Completion Service."""
        self.dao = candidate_interview_dao
        self.sqs = sqs_service
        logger.info("InterviewCompletionService initialized")
    
    async def complete_interview(
        self,
        candidate_interview_id: str,
        completion_reason: CompletionReason,
        session_duration_seconds: int = 0,
        total_planner_fields: int = 0,
        transitions_completed: int = 0,
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Complete an interview by updating database and sending SQS notification.
        
        This is the main orchestration method that:
        1. Validates the interview exists and is in progress
        2. Updates the interview status to COMPLETED in database
        3. Sends completion notification to SQS queue
        4. Logs the completion event
        
        Args:
            candidate_interview_id: ID of the candidate interview to complete
            completion_reason: Reason for completion (CompletionReason enum)
            session_duration_seconds: Total duration of interview session in seconds
            total_planner_fields: Total number of planner fields in interview
            transitions_completed: Number of phase transitions completed
            additional_metadata: Optional dictionary with additional completion metadata
            
        Returns:
            Dictionary containing completion status and details
        """
        completion_timestamp = datetime.utcnow().isoformat()
        
        logger.info("🏁 Starting interview completion workflow",
                   candidate_interview_id=candidate_interview_id,
                   completion_reason=completion_reason.value,
                   session_duration_seconds=session_duration_seconds,
                   completion_timestamp=completion_timestamp)
        
        result = {
            "candidate_interview_id": candidate_interview_id,
            "completion_reason": completion_reason.value,
            "completion_timestamp": completion_timestamp,
            "database_updated": False,
            "notification_sent": False,
            "errors": []
        }
        
        db = None
        try:
            # Step 1: Get database session
            db = await get_db_session()
            
            # Step 2: Validate interview exists
            interview = await self._validate_interview(db, candidate_interview_id)
            if not interview:
                error_msg = "Interview not found"
                logger.error(error_msg, candidate_interview_id=candidate_interview_id)
                result["errors"].append(error_msg)
                return result
            
            # Step 3: Check if already completed (idempotency)
            if interview.status == CandidateInterviewStatus.COMPLETED:
                logger.warning("⚠️ Interview already marked as COMPLETED - duplicate completion attempt",
                             candidate_interview_id=candidate_interview_id,
                             current_status=interview.status.value)
                result["database_updated"] = False
                result["already_completed"] = True
                return result
            
            # Step 4: Send SQS notification FIRST (before DB update)
            try:
                sqs_result = await self._send_completion_notification(
                    interview=interview,
                    completion_reason=completion_reason,
                    completion_timestamp=completion_timestamp,
                    session_duration_seconds=session_duration_seconds,
                    total_planner_fields=total_planner_fields,
                    transitions_completed=transitions_completed,
                    additional_metadata=additional_metadata
                )
                
                result["notification_sent"] = sqs_result.get("notification_sent", False)
                result["sqs_message_id"] = sqs_result.get("message_id")
                
                if not sqs_result.get("success"):
                    error_msg = sqs_result.get("message", "SQS notification failed")
                    result["errors"].append(error_msg)
                    logger.warning("⚠️ SQS notification failed, but continuing with DB update",
                                 candidate_interview_id=candidate_interview_id)
                    
            except Exception as sqs_error:
                error_msg = f"SQS notification failed: {str(sqs_error)}"
                logger.error("❌ Failed to send SQS notification",
                           error=str(sqs_error),
                           candidate_interview_id=candidate_interview_id)
                result["errors"].append(error_msg)
                # Continue with DB update even if SQS fails
            
            # Step 5: Update interview status to COMPLETED (after SQS notification)
            try:
                updated_interview = await self._update_interview_status(
                    db, 
                    candidate_interview_id, 
                    CandidateInterviewStatus.COMPLETED
                )
                result["database_updated"] = True
                result["previous_status"] = interview.status.value
                result["new_status"] = CandidateInterviewStatus.COMPLETED.value
                
                logger.info("✅ Interview status updated to COMPLETED in database",
                           candidate_interview_id=candidate_interview_id,
                           previous_status=interview.status.value)
                
            except Exception as db_error:
                error_msg = f"Database update failed: {str(db_error)}"
                logger.error("❌ Failed to update interview status",
                           error=str(db_error),
                           candidate_interview_id=candidate_interview_id)
                result["errors"].append(error_msg)
                # DB update failed after SQS notification - log critical error
                logger.critical("🚨 CRITICAL: SQS notification sent but DB update failed",
                              candidate_interview_id=candidate_interview_id,
                              sqs_message_id=result.get("sqs_message_id"))
            
            # Step 6: Log final completion status
            # Success requires both notification sent AND database updated
            success = result["notification_sent"] and result["database_updated"]
            
            if success:
                logger.info("🎉 Interview completion workflow finished successfully",
                           candidate_interview_id=candidate_interview_id,
                           completion_reason=completion_reason.value,
                           database_updated=True,
                           notification_sent=True)
            else:
                logger.warning("⚠️ Interview completion workflow finished with issues",
                             candidate_interview_id=candidate_interview_id,
                             database_updated=result["database_updated"],
                             notification_sent=result["notification_sent"],
                             errors=result["errors"])
            
            result["success"] = success
            return result
            
        except Exception as e:
            error_msg = f"Unexpected error in completion workflow: {str(e)}"
            logger.error("❌ Interview completion workflow failed",
                        error=str(e),
                        error_type=type(e).__name__,
                        candidate_interview_id=candidate_interview_id)
            result["errors"].append(error_msg)
            result["success"] = False
            return result
            
        finally:
            if db:
                await db.close()
    
    async def _validate_interview(
        self, 
        db: AsyncSession, 
        candidate_interview_id: str
    ) -> Optional[CandidateInterview]:
        """Validate that interview exists.
        
        Args:
            db: Database session
            candidate_interview_id: ID of interview to validate
            
        Returns:
            CandidateInterview object if found, None otherwise
        """
        try:
            interview = await self.dao.get_by_id(db, candidate_interview_id)  # type: ignore
            
            if not interview:
                logger.warning("Interview not found during validation",
                             candidate_interview_id=candidate_interview_id)
                return None
            
            logger.debug("Interview validated successfully",
                        candidate_interview_id=candidate_interview_id,
                        current_status=interview.status.value,
                        user_id=interview.userId)
            
            return interview
            
        except Exception as e:
            logger.error("Error validating interview",
                        error=str(e),
                        candidate_interview_id=candidate_interview_id)
            return None
    
    async def _update_interview_status(
        self,
        db: AsyncSession,
        candidate_interview_id: str,
        status: CandidateInterviewStatus
    ) -> Optional[CandidateInterview]:
        """Update interview status in database.
        
        Args:
            db: Database session
            candidate_interview_id: ID of interview to update
            status: New status to set
            
        Returns:
            Updated CandidateInterview object
        """
        try:
            updated_interview = await self.dao.update_status(
                db,
                candidate_interview_id,
                status
            )
            
            logger.info("Interview status updated",
                       candidate_interview_id=candidate_interview_id,
                       new_status=status.value)
            
            return updated_interview
            
        except Exception as e:
            logger.error("Failed to update interview status",
                        error=str(e),
                        candidate_interview_id=candidate_interview_id,
                        status=status.value)
            raise
    
    async def _send_completion_notification(
        self,
        interview: CandidateInterview,
        completion_reason: CompletionReason,
        completion_timestamp: str,
        session_duration_seconds: int,
        total_planner_fields: int,
        transitions_completed: int,
        additional_metadata: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Send interview completion notification to SQS.
        
        Args:
            interview: CandidateInterview object
            completion_reason: Reason for completion (stored for logging only)
            completion_timestamp: ISO-8601 timestamp (stored for logging only)
            session_duration_seconds: Duration in seconds (stored for logging only)
            total_planner_fields: Total planner fields (stored for logging only)
            transitions_completed: Completed transitions (stored for logging only)
            additional_metadata: Additional metadata (stored for logging only)
            
        Returns:
            Dictionary with notification result
        """
        try:
            # Send only candidate_interview_id to SQS
            result = await self.sqs.send_interview_completion_notification(
                candidate_interview_id=interview.id
            )
            
            return result
            
        except Exception as e:
            logger.error("Error sending completion notification",
                        error=str(e),
                        candidate_interview_id=interview.id)
            return {
                "success": False,
                "message": str(e),
                "notification_sent": False
            }
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get status of completion service and dependencies.
        
        Returns:
            Dictionary with service status
        """
        return {
            "service": "InterviewCompletionService",
            "sqs_enabled": self.sqs.is_enabled(),
            "sqs_status": self.sqs.get_service_status()
        }


# Create singleton instance
interview_completion_service = InterviewCompletionService()

