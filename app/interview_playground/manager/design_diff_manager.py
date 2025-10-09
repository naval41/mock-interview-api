"""
Design Diff Manager for handling design content differences and database operations.
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from app.dao.question_solution_dao import QuestionSolutionDAO
from app.models.question_solution import QuestionSolution
from app.models.enums import CodeLanguage
from app.core.database import get_db_session
import structlog
import json

logger = structlog.get_logger()


@dataclass
class DesignDiffResult:
    """Result of design diff operation"""
    has_changes: bool
    is_first_submission: bool
    question_id: str
    current_design: str  # JSON string of the design
    description: str  # Generated description
    mermaid: str  # Generated mermaid diagram
    solution_id: Optional[str] = None
    timestamp: Optional[int] = None


class DesignDiffManager:
    """
    Manager class for handling design content differences and database operations.
    
    Responsibilities:
    1. Store/update design content in database with language 'DESIGN'
    2. Maintain previous design content in memory for optimization
    3. Return diff details to processor
    """
    
    def __init__(self):
        """Initialize the DesignDiffManager"""
        self.dao = QuestionSolutionDAO()
        # Cache to store last design content per question to avoid unnecessary DB calls
        self._design_cache: Dict[str, str] = {}
    
    async def process_design_content(
        self, 
        question_id: str, 
        candidate_interview_id: str,
        design_content: dict,  # Original Excalidraw JSON
        description: str,  # Generated description
        mermaid: str,  # Generated mermaid
        timestamp: Optional[int] = None
    ) -> DesignDiffResult:
        """
        Process design content and return diff information.
        
        Args:
            question_id: ID of the question
            candidate_interview_id: ID of the candidate interview
            design_content: Original Excalidraw JSON dict
            description: Generated description
            mermaid: Generated mermaid diagram
            timestamp: Timestamp of the submission
            
        Returns:
            DesignDiffResult containing diff information
        """
        # Get database session
        db = await get_db_session()
        try:
            # Convert design content to JSON string for storage
            design_json = json.dumps(design_content, indent=2)
            
            logger.info("Processing design content", 
                       question_id=question_id,
                       design_length=len(design_json),
                       description_length=len(description),
                       mermaid_length=len(mermaid))
        
            # Check if we have previous content in cache
            cache_key = f"{question_id}_{candidate_interview_id}"
            cached_content = self._design_cache.get(cache_key)
            
            if cached_content:
                # Use cached content for quick comparison
                if cached_content == design_json:
                    # No changes, skip processing
                    logger.info("No changes detected (design cache)", question_id=question_id)
                    existing_solution = await self.dao.get_by_question_and_candidate(
                        db, question_id, candidate_interview_id
                    )
                    return DesignDiffResult(
                        has_changes=False,
                        is_first_submission=False,
                        question_id=question_id,
                        current_design=design_json,
                        description=description,
                        mermaid=mermaid,
                        solution_id=existing_solution.id if existing_solution else None,
                        timestamp=timestamp
                    )
            
            # Get existing solution from database
            existing_solution = await self.dao.get_by_question_and_candidate(
                db, question_id, candidate_interview_id
            )
            
            if not existing_solution:
                # First submission case
                logger.info("First design submission detected", question_id=question_id)
                
                # Store in database with language='DESIGN'
                # Store the complete design package as JSON with metadata
                design_package = {
                    "original_design": design_content,
                    "description": description,
                    "mermaid": mermaid,
                    "timestamp": timestamp
                }
                
                new_solution = await self.dao.create_or_update_solution(
                    db=db,
                    question_id=question_id,
                    candidate_interview_id=candidate_interview_id,
                    answer_content=json.dumps(design_package, indent=2),
                    language="DESIGN"
                )
                
                # Update cache with original design JSON
                self._design_cache[cache_key] = design_json
                
                logger.info("✅ Design stored in database", 
                           solution_id=new_solution.id,
                           question_id=question_id)
                
                return DesignDiffResult(
                    has_changes=True,
                    is_first_submission=True,
                    question_id=question_id,
                    current_design=design_json,
                    description=description,
                    mermaid=mermaid,
                    solution_id=new_solution.id,
                    timestamp=timestamp
                )
            
            else:
                # Subsequent submission case
                try:
                    # Extract original design from stored package
                    stored_package = json.loads(existing_solution.answer or "{}")
                    previous_design = stored_package.get("original_design", {})
                    previous_design_json = json.dumps(previous_design, indent=2)
                except (json.JSONDecodeError, AttributeError):
                    # If stored format is different, treat as first submission
                    previous_design_json = existing_solution.answer or ""
                
                # Check if content actually changed
                if previous_design_json == design_json:
                    logger.info("No design changes detected (DB)", question_id=question_id)
                    # Update cache even for no-change case
                    self._design_cache[cache_key] = design_json
 
                    return DesignDiffResult(
                        has_changes=False,
                        is_first_submission=False,
                        question_id=question_id,
                        current_design=design_json,
                        description=description,
                        mermaid=mermaid,
                        solution_id=existing_solution.id,
                        timestamp=timestamp
                    )
                
                logger.info("Design changes detected, updating database", question_id=question_id)
                
                # Store updated content in database
                design_package = {
                    "original_design": design_content,
                    "description": description,
                    "mermaid": mermaid,
                    "timestamp": timestamp
                }
                
                updated_solution = await self.dao.create_or_update_solution(
                    db=db,
                    question_id=question_id,
                    candidate_interview_id=candidate_interview_id,
                    answer_content=json.dumps(design_package, indent=2),
                    language="DESIGN"
                )
                
                # Update cache
                self._design_cache[cache_key] = design_json
                
                logger.info("✅ Design updated in database", 
                           solution_id=updated_solution.id,
                           question_id=question_id)
                
                return DesignDiffResult(
                    has_changes=True,
                    is_first_submission=False,
                    question_id=question_id,
                    current_design=design_json,
                    description=description,
                    mermaid=mermaid,
                    solution_id=updated_solution.id,
                    timestamp=timestamp
                )
                
        except Exception as e:
            logger.error("Error processing design content", 
                        question_id=question_id, 
                        error=str(e),
                        error_type=type(e).__name__)
            raise
        finally:
            await db.close()
    
    def clear_cache(self, question_id: Optional[str] = None, candidate_interview_id: Optional[str] = None):
        """
        Clear design cache for optimization.
        
        Args:
            question_id: Specific question to clear
            candidate_interview_id: Specific candidate interview to clear
            If both provided, clears specific cache entry. If neither provided, clears all.
        """
        if question_id and candidate_interview_id:
            cache_key = f"{question_id}_{candidate_interview_id}"
            self._design_cache.pop(cache_key, None)
            logger.info("Cleared design cache for question and candidate", 
                       question_id=question_id, 
                       candidate_interview_id=candidate_interview_id)
        else:
            self._design_cache.clear()
            logger.info("Cleared all design cache")
    
    def get_cache_status(self) -> Dict[str, Any]:
        """
        Get current cache status for debugging.
        
        Returns:
            Dictionary with cache information
        """
        return {
            "cached_keys": list(self._design_cache.keys()),
            "cache_size": len(self._design_cache)
        }


