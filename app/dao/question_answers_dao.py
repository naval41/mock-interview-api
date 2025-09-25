from typing import Optional, List
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.dao.base_dao import BaseDAO
from app.models.interview_question import QuestionAnswers
import structlog

logger = structlog.get_logger()


class QuestionAnswersDAO(BaseDAO[QuestionAnswers]):
    def __init__(self):
        super().__init__(QuestionAnswers)

    async def get_by_question_id(
        self, 
        db: AsyncSession, 
        question_id: str
    ) -> Optional[QuestionAnswers]:
        """Get the latest answer for a specific question"""
        try:
            result = await db.execute(
                select(QuestionAnswers).where(
                    QuestionAnswers.questionId == question_id
                ).order_by(QuestionAnswers.version.desc())
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error("Error getting answer by question_id", question_id=question_id, error=str(e))
            raise

    async def get_all_by_question_id(
        self, 
        db: AsyncSession, 
        question_id: str
    ) -> List[QuestionAnswers]:
        """Get all answers for a specific question ordered by version"""
        try:
            result = await db.execute(
                select(QuestionAnswers).where(
                    QuestionAnswers.questionId == question_id
                ).order_by(QuestionAnswers.version.asc())
            )
            return result.scalars().all()
        except Exception as e:
            logger.error("Error getting all answers by question_id", question_id=question_id, error=str(e))
            raise

    async def create_or_update_answer(
        self, 
        db: AsyncSession, 
        question_id: str,
        answer_content: str,
        language: str,
        answer_sequence: Optional[int] = None
    ) -> QuestionAnswers:
        """Create a new answer or update existing one with incremented version"""
        try:
            # Get the latest answer to determine version
            existing_answer = await self.get_by_question_id(db, question_id)
            
            if existing_answer:
                # Update existing answer with new version
                new_version = (existing_answer.version or 1) + 1
                answer_data = {
                    "questionId": question_id,
                    "answerContent": answer_content,
                    "language": language,
                    "version": new_version,
                    "answerSequence": answer_sequence or existing_answer.answerSequence
                }
            else:
                # Create first answer
                answer_data = {
                    "questionId": question_id,
                    "answerContent": answer_content,
                    "language": language,
                    "version": 1,
                    "answerSequence": answer_sequence or 1
                }
            
            answer = await self.create(db, obj_in=answer_data)
            logger.info("Created/updated answer", 
                       question_id=question_id,
                       version=answer_data["version"])
            return answer
        except Exception as e:
            logger.error("Error creating/updating answer", 
                        question_id=question_id,
                        error=str(e))
            raise

