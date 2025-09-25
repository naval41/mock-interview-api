"""
Code Diff Manager for handling code content differences and database operations.
"""

import difflib
from typing import Optional, Dict, Any
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from app.dao.question_solution_dao import QuestionSolutionDAO
from app.models.question_solution import QuestionSolution
from app.models.enums import CodeLanguage
from app.core.database import get_db_session
import structlog

logger = structlog.get_logger()


@dataclass
class DiffResult:
    """Result of diff operation"""
    has_changes: bool
    diff_content: Optional[str]
    is_first_submission: bool
    question_id: str
    solution_id: Optional[str] = None
    timestamp: Optional[int] = None


class CodeDiffManager:
    """
    Manager class for handling code content differences and database operations.
    
    Responsibilities:
    1. Find differences between code versions
    2. Store/update code content in database
    3. Maintain previous code content in memory for optimization
    4. Return diff details to processor
    """
    
    def __init__(self):
        """Initialize the CodeDiffManager"""
        self.dao = QuestionSolutionDAO()
        # Cache to store last code content per question to avoid unnecessary DB calls
        self._code_cache: Dict[str, str] = {}
    
    def _normalize_language(self, language: str) -> CodeLanguage:
        """
        Normalize language string to CodeLanguage enum.
        
        Args:
            language: Language string from frontend (e.g., 'javascript', 'python')
            
        Returns:
            CodeLanguage enum value
        """
        # Map common frontend language names to database enum values
        language_mapping = {
            'javascript': CodeLanguage.JAVASCRIPT,
            'typescript': CodeLanguage.TYPESCRIPT, 
            'python': CodeLanguage.PYTHON,
            'java': CodeLanguage.JAVA,
            'go': CodeLanguage.GO,
            'cpp': CodeLanguage.CPP,
            'c++': CodeLanguage.CPP,
            'csharp': CodeLanguage.CSHARP,
            'c#': CodeLanguage.CSHARP,
            'ruby': CodeLanguage.RUBY,
            'php': CodeLanguage.PHP,
            'sql': CodeLanguage.SQL
        }
        
        # Try to get from mapping first, then try to get enum by name
        normalized = language_mapping.get(language.lower())
        if not normalized:
            try:
                normalized = CodeLanguage[language.upper()]
            except KeyError:
                # Default to JAVASCRIPT if unknown language
                normalized = CodeLanguage.JAVASCRIPT
                logger.warning("Unknown language, defaulting to JAVASCRIPT", original=language)
        
        logger.debug("Language normalized", original=language, normalized=normalized.value)
        return normalized
        
    async def process_code_content(
        self, 
        question_id: str, 
        candidate_interview_id: str,
        code_content: str, 
        language: str,
        timestamp: Optional[int] = None
    ) -> DiffResult:
        """
        Process code content and return diff information.
        
        Args:
            question_id: ID of the question
            candidate_interview_id: ID of the candidate interview
            code_content: Current code content
            language: Programming language
            timestamp: Timestamp of the submission
            
        Returns:
            DiffResult containing diff information
        """
        # Get database session
        db = await get_db_session()
        try:
            # Normalize language to match database enum format
            normalized_language = self._normalize_language(language)
            logger.info("Processing code content", question_id=question_id, language=language, normalized_language=normalized_language)
        
 
            # Check if we have previous content in cache
            cache_key = f"{question_id}_{candidate_interview_id}"
            cached_content = self._code_cache.get(cache_key)
            
            if cached_content:
                # Use cached content for quick comparison
                if cached_content == code_content:
                    # No changes, skip processing
                    logger.info("No changes detected (content cache)", question_id=question_id)
                    existing_solution = await self.dao.get_by_question_and_candidate(
                        db, question_id, candidate_interview_id
                    )
                    return DiffResult(
                        has_changes=False,
                        diff_content=None,
                        is_first_submission=False,
                        question_id=question_id,
                        solution_id=existing_solution.id if existing_solution else None,
                        timestamp=timestamp
                    )
            
            # Get existing solution from database
            existing_solution = await self.dao.get_by_question_and_candidate(
                db, question_id, candidate_interview_id
            )
            
            if not existing_solution:
                # First submission case
                logger.info("First submission detected", question_id=question_id)
                
                # Store in database
                new_solution = await self.dao.create_or_update_solution(
                    db=db,
                    question_id=question_id,
                    candidate_interview_id=candidate_interview_id,
                    answer_content=code_content,
                    language=normalized_language.value  # Pass the string value instead of enum
                )
                
                # Update cache
                self._code_cache[cache_key] = code_content
                
                return DiffResult(
                    has_changes=True,
                    diff_content=None,  # No diff for first submission
                    is_first_submission=True,
                    question_id=question_id,
                    solution_id=new_solution.id,
                    timestamp=timestamp
                )
            
            else:
                # Subsequent submission case
                previous_content = existing_solution.answer or ""
                
                # Check if content actually changed
                if previous_content == code_content:
                    logger.info("No changes detected (DB)", question_id=question_id)
                    # Update cache even for no-change case
                    self._code_cache[cache_key] = code_content
 
                    return DiffResult(
                        has_changes=False,
                        diff_content=None,
                        is_first_submission=False,
                        question_id=question_id,
                        solution_id=existing_solution.id,
                        timestamp=timestamp
                    )
                
                # Generate diff
                diff_content = self._generate_diff(previous_content, code_content, language)
                
                logger.info("Changes detected, generating diff", question_id=question_id)
                
                # Store updated content in database
                updated_solution = await self.dao.create_or_update_solution(
                    db=db,
                    question_id=question_id,
                    candidate_interview_id=candidate_interview_id,
                    answer_content=code_content,
                    language=normalized_language.value  # Pass the string value instead of enum
                )
                
                # Update cache
                self._code_cache[cache_key] = code_content
                
                return DiffResult(
                    has_changes=True,
                    diff_content=diff_content,
                    is_first_submission=False,
                    question_id=question_id,
                    solution_id=updated_solution.id,
                    timestamp=timestamp
                )
                
        except Exception as e:
            logger.error("Error processing code content", question_id=question_id, error=str(e))
            raise
        finally:
            await db.close()
    
    def _generate_diff(self, old_content: str, new_content: str, language: str) -> str:
        """
        Generate unified diff between old and new content.
        
        Args:
            old_content: Previous version content
            new_content: Current version content  
            language: Programming language for context
            
        Returns:
            Unified diff string
        """
        try:
            old_lines = old_content.splitlines(keepends=True)
            new_lines = new_content.splitlines(keepends=True)
            
            diff = difflib.unified_diff(
                old_lines,
                new_lines,
                fromfile=f"previous_version.{language}",
                tofile=f"current_version.{language}",
                lineterm=""
            )
            
            return "".join(diff)
            
        except Exception as e:
            logger.error("Error generating diff", error=str(e))
            return f"Error generating diff: {str(e)}"
    
    def clear_cache(self, question_id: Optional[str] = None, candidate_interview_id: Optional[str] = None):
        """
        Clear code cache for optimization.
        
        Args:
            question_id: Specific question to clear
            candidate_interview_id: Specific candidate interview to clear
            If both provided, clears specific cache entry. If neither provided, clears all.
        """
        if question_id and candidate_interview_id:
            cache_key = f"{question_id}_{candidate_interview_id}"
            self._code_cache.pop(cache_key, None)
            logger.info("Cleared cache for question and candidate", 
                       question_id=question_id, 
                       candidate_interview_id=candidate_interview_id)
        else:
            self._code_cache.clear()
            logger.info("Cleared all cache")
    
    def get_cache_status(self) -> Dict[str, Any]:
        """
        Get current cache status for debugging.
        
        Returns:
            Dictionary with cache information
        """
        return {
            "cached_keys": list(self._code_cache.keys()),
            "cache_size": len(self._code_cache)
        }
