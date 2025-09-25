from typing import Optional, List
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.dao.base_dao import BaseDAO
from app.models.question_solution import QuestionSolution
from app.models.enums import CodeLanguage
import structlog

logger = structlog.get_logger()


class QuestionSolutionDAO(BaseDAO[QuestionSolution]):
    def __init__(self):
        super().__init__(QuestionSolution)

    async def get_by_question_id(
        self, 
        db: AsyncSession, 
        question_id: str
    ) -> Optional[QuestionSolution]:
        """Get the latest solution for a specific question"""
        try:
            result = await db.execute(
                select(QuestionSolution).where(
                    QuestionSolution.questionId == question_id
                ).order_by(QuestionSolution.id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error("Error getting solution by question_id", question_id=question_id, error=str(e))
            raise

    async def get_by_question_and_candidate(
        self, 
        db: AsyncSession, 
        question_id: str,
        candidate_interview_id: str
    ) -> Optional[QuestionSolution]:
        """Get solution for a specific question and candidate interview"""
        try:
            result = await db.execute(
                select(QuestionSolution).where(
                    QuestionSolution.questionId == question_id,
                    QuestionSolution.candidateInterviewId == candidate_interview_id
                )
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error("Error getting solution by question and candidate", 
                        question_id=question_id, 
                        candidate_interview_id=candidate_interview_id, 
                        error=str(e))
            raise

    async def get_all_by_question_id(
        self, 
        db: AsyncSession, 
        question_id: str
    ) -> List[QuestionSolution]:
        """Get all solutions for a specific question"""
        try:
            result = await db.execute(
                select(QuestionSolution).where(
                    QuestionSolution.questionId == question_id
                ).order_by(QuestionSolution.id)
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error("Error getting all solutions by question_id", question_id=question_id, error=str(e))
            raise

    async def create_or_update_solution(
        self, 
        db: AsyncSession, 
        question_id: str,
        candidate_interview_id: str,
        answer_content: str,
        language: str
    ) -> QuestionSolution:
        """Create a new solution or update existing one"""
        try:
            # Check if solution already exists for this question and candidate
            existing_solution = await self.get_by_question_and_candidate(
                db, question_id, candidate_interview_id
            )
            
            if existing_solution:
                # Update existing solution - ensure language is converted to proper enum
                language_enum = CodeLanguage(language) if isinstance(language, str) else language
                solution_data = {
                    "answer": answer_content,
                    "type": language_enum
                }
                updated_solution = await self.update(db, db_obj=existing_solution, obj_in=solution_data)
                logger.info("Updated solution", 
                           question_id=question_id,
                           candidate_interview_id=candidate_interview_id)
                return updated_solution
            else:
                # Create new solution - ensure language is converted to proper enum
                language_enum = CodeLanguage(language) if isinstance(language, str) else language
                solution_data = {
                    "questionId": question_id,
                    "candidateInterviewId": candidate_interview_id,
                    "answer": answer_content,
                    "type": language_enum
                }
                
                solution = await self.create(db, obj_in=solution_data)
                logger.info("Created solution", 
                           question_id=question_id,
                           candidate_interview_id=candidate_interview_id)
                return solution
        except Exception as e:
            logger.error("Error creating/updating solution", 
                        question_id=question_id,
                        candidate_interview_id=candidate_interview_id,
                        error=str(e))
            raise
