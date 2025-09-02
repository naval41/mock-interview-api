from typing import Optional, List
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.dao.base_dao import BaseDAO
from app.models.candidate_interview_planner import CandidateInterviewPlanner
import structlog

logger = structlog.get_logger()


class CandidateInterviewPlannerDAO(BaseDAO[CandidateInterviewPlanner]):
    def __init__(self):
        super().__init__(CandidateInterviewPlanner)

    async def get_by_candidate_interview_id(
        self, 
        db: AsyncSession, 
        candidate_interview_id: str
    ) -> List[CandidateInterviewPlanner]:
        """Get all planners for a specific candidate interview"""
        try:
            result = await db.execute(
                select(CandidateInterviewPlanner).where(
                    CandidateInterviewPlanner.candidateInterviewId == candidate_interview_id
                ).order_by(CandidateInterviewPlanner.createdAt)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error("Error getting planners by candidate_interview_id", candidate_interview_id=candidate_interview_id, error=str(e))
            raise

    async def get_by_workflow_id(
        self, 
        db: AsyncSession, 
        workflow_id: str
    ) -> List[CandidateInterviewPlanner]:
        """Get all planners for a specific workflow"""
        try:
            result = await db.execute(
                select(CandidateInterviewPlanner).where(
                    CandidateInterviewPlanner.workflowId == workflow_id
                )
            )
            return result.scalars().all()
        except Exception as e:
            logger.error("Error getting planners by workflow_id", workflow_id=workflow_id, error=str(e))
            raise

    async def get_by_workflow_step_id(
        self, 
        db: AsyncSession, 
        workflow_step_id: str
    ) -> List[CandidateInterviewPlanner]:
        """Get all planners for a specific workflow step"""
        try:
            result = await db.execute(
                select(CandidateInterviewPlanner).where(
                    CandidateInterviewPlanner.workflowStepId == workflow_step_id
                )
            )
            return result.scalars().all()
        except Exception as e:
            logger.error("Error getting planners by workflow_step_id", workflow_step_id=workflow_step_id, error=str(e))
            raise

    async def get_by_question_id(
        self, 
        db: AsyncSession, 
        question_id: str
    ) -> List[CandidateInterviewPlanner]:
        """Get all planners that use a specific question"""
        try:
            result = await db.execute(
                select(CandidateInterviewPlanner).where(
                    CandidateInterviewPlanner.questionId == question_id
                )
            )
            return result.scalars().all()
        except Exception as e:
            logger.error("Error getting planners by question_id", question_id=question_id, error=str(e))
            raise

    async def get_by_knowledge_bank_id(
        self, 
        db: AsyncSession, 
        knowledge_bank_id: str
    ) -> List[CandidateInterviewPlanner]:
        """Get all planners that use a specific knowledge bank"""
        try:
            result = await db.execute(
                select(CandidateInterviewPlanner).where(
                    CandidateInterviewPlanner.knowledgeBankId == knowledge_bank_id
                )
            )
            return result.scalars().all()
        except Exception as e:
            logger.error("Error getting planners by knowledge_bank_id", knowledge_bank_id=knowledge_bank_id, error=str(e))
            raise

    async def get_interview_plan(
        self, 
        db: AsyncSession, 
        candidate_interview_id: str
    ) -> List[CandidateInterviewPlanner]:
        """Get the complete interview plan for a candidate interview, ordered by creation time"""
        try:
            result = await db.execute(
                select(CandidateInterviewPlanner).where(
                    CandidateInterviewPlanner.candidateInterviewId == candidate_interview_id
                ).order_by(CandidateInterviewPlanner.createdAt)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error("Error getting interview plan", candidate_interview_id=candidate_interview_id, error=str(e))
            raise

    async def create_interview_plan(
        self, 
        db: AsyncSession, 
        candidate_interview_id: str,
        workflow_id: str,
        workflow_step_id: str,
        question_id: str,
        knowledge_bank_id: str,
        interview_instructions: Optional[str] = None
    ) -> CandidateInterviewPlanner:
        """Create a new interview plan entry"""
        try:
            planner_data = {
                "candidateInterviewId": candidate_interview_id,
                "workflowId": workflow_id,
                "workflowStepId": workflow_step_id,
                "questionId": question_id,
                "knowledgeBankId": knowledge_bank_id,
                "interviewInstructions": interview_instructions
            }
            
            planner = await self.create(db, obj_in=planner_data)
            logger.info("Created interview plan entry", 
                       candidate_interview_id=candidate_interview_id,
                       workflow_step_id=workflow_step_id,
                       question_id=question_id)
            return planner
        except Exception as e:
            logger.error("Error creating interview plan entry", 
                        candidate_interview_id=candidate_interview_id,
                        error=str(e))
            raise

    async def update_interview_instructions(
        self, 
        db: AsyncSession, 
        planner_id: str, 
        instructions: str
    ) -> Optional[CandidateInterviewPlanner]:
        """Update the interview instructions for a specific planner"""
        try:
            planner = await self.get_by_id(db, planner_id)
            if planner:
                planner.interviewInstructions = instructions
                db.add(planner)
                await db.commit()
                await db.refresh(planner)
                logger.info("Updated interview instructions", planner_id=planner_id)
            return planner
        except Exception as e:
            await db.rollback()
            logger.error("Error updating interview instructions", planner_id=planner_id, error=str(e))
            raise

    async def delete_interview_plan(
        self, 
        db: AsyncSession, 
        candidate_interview_id: str
    ) -> bool:
        """Delete all planners for a specific candidate interview"""
        try:
            planners = await self.get_by_candidate_interview_id(db, candidate_interview_id)
            for planner in planners:
                await db.delete(planner)
            await db.commit()
            logger.info("Deleted interview plan", candidate_interview_id=candidate_interview_id, count=len(planners))
            return True
        except Exception as e:
            await db.rollback()
            logger.error("Error deleting interview plan", candidate_interview_id=candidate_interview_id, error=str(e))
            raise

    async def get_planners_by_multiple_criteria(
        self,
        db: AsyncSession,
        candidate_interview_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        workflow_step_id: Optional[str] = None,
        question_id: Optional[str] = None,
        knowledge_bank_id: Optional[str] = None
    ) -> List[CandidateInterviewPlanner]:
        """Get planners based on multiple optional criteria"""
        try:
            query = select(CandidateInterviewPlanner)
            
            if candidate_interview_id:
                query = query.where(CandidateInterviewPlanner.candidateInterviewId == candidate_interview_id)
            if workflow_id:
                query = query.where(CandidateInterviewPlanner.workflowId == workflow_id)
            if workflow_step_id:
                query = query.where(CandidateInterviewPlanner.workflowStepId == workflow_step_id)
            if question_id:
                query = query.where(CandidateInterviewPlanner.questionId == question_id)
            if knowledge_bank_id:
                query = query.where(CandidateInterviewPlanner.knowledgeBankId == knowledge_bank_id)
            
            result = await db.execute(query)
            return result.scalars().all()
        except Exception as e:
            logger.error("Error getting planners by multiple criteria", error=str(e))
            raise

    async def get_next_planner_in_sequence(
        self,
        db: AsyncSession,
        candidate_interview_id: str,
        current_planner_id: Optional[str] = None
    ) -> Optional[CandidateInterviewPlanner]:
        """Get the next planner in the interview sequence"""
        try:
            query = select(CandidateInterviewPlanner).where(
                CandidateInterviewPlanner.candidateInterviewId == candidate_interview_id
            ).order_by(CandidateInterviewPlanner.createdAt)
            
            if current_planner_id:
                # Get the current planner to find its position
                current_planner = await self.get_by_id(db, current_planner_id)
                if current_planner:
                    # Get planners created after the current one
                    query = query.where(CandidateInterviewPlanner.createdAt > current_planner.createdAt)
            
            result = await db.execute(query.limit(1))
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error("Error getting next planner in sequence", 
                        candidate_interview_id=candidate_interview_id,
                        current_planner_id=current_planner_id,
                        error=str(e))
            raise


# Create a singleton instance
candidate_interview_planner_dao = CandidateInterviewPlannerDAO()
