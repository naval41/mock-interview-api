"""
Code Context Processor implementation that extends BaseProcessor.
"""
from typing import Optional
from pipecat.frames.frames import Frame, InputTextRawFrame, LLMMessagesAppendFrame, LLMMessagesUpdateFrame
from pipecat.processors.frame_processor import FrameDirection
from pipecat.processors.frameworks.rtvi import RTVIClientMessageFrame
from app.interview_playground.processors.base_processor import BaseProcessor
from app.interview_playground.manager.code_diff_manager import CodeDiffManager, DiffResult
from app.models.enums import ToolEvent
import structlog

logger = structlog.get_logger()


class CodeContextProcessor(BaseProcessor):
    """Code Context Processor for handling code-related messages and context."""
    
    def __init__(self, max_code_snippets: int = 10, language_detection: bool = True, question_id: Optional[str] = None):
        """Initialize Code Context Processor.
        
        Args:
            max_code_snippets: Maximum number of code snippets to keep in context
            language_detection: Whether to automatically detect programming language
            question_id: Current question ID for code submissions
        """
        super().__init__(name="code_context_processor")
        self.max_code_snippets = max_code_snippets
        self.language_detection = language_detection
        self.code_snippets = []
        self.language_context = {}
        self.question_id = question_id
        
        # Initialize the code diff manager
        self.code_diff_manager = CodeDiffManager()
    
    def set_question_id(self, question_id: str):
        """Set the current question ID for code submissions."""
        self.question_id = question_id
        logger.info("Question ID set", question_id=question_id)
        
    # Remove the setup_processor method - it's no longer needed
    
    async def process_custom_frame(self, frame: Frame, direction: FrameDirection):
        """Process frames after StartFrame validation."""
        # Handle RTVI client messages for code and problem context
        if isinstance(frame, RTVIClientMessageFrame) and frame.type == ToolEvent.CODE_CONTENT:
            await self._handle_rtvi_message(frame)
        else:
            # Continue processing the frame
            await self.push_frame(frame, direction)
    
    async def _handle_rtvi_message(self, frame: RTVIClientMessageFrame):
        """Handle RTVI client messages, specifically CodeContent events."""
        try:
            logger.info("RTVI client message received", frame=frame)
            message_data = frame.data
            if not isinstance(message_data, dict):
                logger.warning("Invalid message data format", message_data=message_data)
                return
            
            # Process CodeContent event (we know it's CODE_CONTENT due to check in process_custom_frame)
            await self._process_code_content_event(frame)
                
        except Exception as e:
            logger.error("Error handling RTVI message", error=str(e))
    
    async def _process_code_content_event(self, frame: RTVIClientMessageFrame):
        """Process CodeContent event and handle diff logic."""
        try:
            data = frame.data or {}
            content = data.get("content", "")
            language = data.get("language", "unknown")
            timestamp = data.get("timestamp")
            question_Id = data.get("questionId", "")
            candidate_interview_id = data.get("candidateInterviewId", "")
   
            
            logger.info("Processing CodeContent event", 
                       language=language, 
                       content_length=len(content),
                       timestamp=timestamp)
            
            # Validate required data
            if not content:
                logger.warning("Empty code content received")
                return
            
            # Process code content through diff manager (manager handles DB session)
            diff_result = await self.code_diff_manager.process_code_content(
                question_id=question_Id,
                candidate_interview_id=candidate_interview_id,
                code_content=content,
                language=language,
                timestamp=timestamp
            )

            
            # Print diff results for now (as requested)
            await self._print_diff_results(diff_result)
            
            # Send to LLM if there are changes or it's a first submission
            if diff_result.has_changes:
                llm_prompt = self._build_llm_prompt(diff_result, language)
                phase = "initial submission" if diff_result.is_first_submission else "update phase"
                logger.info(f"Sending {phase} reference to LLM", 
                           question_id=diff_result.question_id,
                           is_first_submission=diff_result.is_first_submission,
                           has_diff=bool(diff_result.diff_content),
                           phase=phase)

                messages = [
                    {
                        "role": "user", 
                        "content": llm_prompt
                    }
                ]
                # Send the LLM prompt as InputTextRawFrame
                await self.push_frame(LLMMessagesAppendFrame(messages=messages, run_llm=True), FrameDirection.DOWNSTREAM)
            else:
                logger.debug("No changes detected, skipping LLM reference update", question_id=diff_result.question_id)
                    
        except Exception as e:
            logger.error("Error processing CodeContent event", error=str(e))
    
    def _build_llm_prompt(self, diff_result: DiffResult, language: str) -> str:
        """
        Build LLM prompt with complete code content and optional diff information.
        
        Args:
            diff_result: Result from diff processing (includes current_code)
            language: Programming language
            
        Returns:
            Formatted prompt for LLM
        """
        if diff_result.is_first_submission:
            # First submission prompt - complete code for context but likely incomplete
            prompt = f"""
📝 **CODE REFERENCE UPDATE - INITIAL SUBMISSION**

The candidate has started working on their solution and provided their current progress for reference:

**Programming Language:** {language.upper()}
**Question ID:** {diff_result.question_id}

**Current Code Progress (Full Context):**
```{language}
{diff_result.current_code}
```

**Context:**
- This is the candidate's initial code submission - likely incomplete or in early development
- The code above represents their current progress, not a final solution
- This is provided for your reference to understand their approach and thinking
- The solution may be partial, have placeholders, or be in early stages

**Instructions:**
- Candidate writes this code on the kind of white paper, so expect typos and other syntax related errors. Dont highlight those parts as those are expected.
- Observe the candidate's problem-solving approach
- Take note of the direction they're heading
- Only provide feedback or ask follow-up questions if the solution seems nearly complete or if there are critical issues that need immediate attention
- Allow the candidate to continue developing their solution naturally
- Do not provide any feedback or ask follow-up questions unless the solution seems nearly complete or if there are critical issues that need immediate attention

This message is only for you reference and you dont need to emit any response as part of that. 
"""
        else:
            # Code update prompt - incremental development with full context only
            prompt = f"""
🔄 **CODE REFERENCE UPDATE - INCREMENTAL DEVELOPMENT**

The candidate is actively developing their solution and has made incremental changes to their code.

**Programming Language:** {language.upper()}
**Question ID:** {diff_result.question_id}

**Current Code State (Complete Code for Full Context):**
```{language}
{diff_result.current_code}
```

**Context:**
- This is INCREMENTAL DEVELOPMENT - the candidate is iteratively working on their solution
- The complete code above represents their current progress, but the solution may still be incomplete
- The candidate has made some changes since the last update and is actively developing
- The candidate will likely make further changes as they continue working
- This represents their current state in the ongoing problem-solving process

**Instructions:**
- Candidate writes this code on the kind of white paper, so expect typos and other syntax related errors. Dont highlight those parts as those are expected.
- You have the complete current code for full context, but treat this as ONGOING INCREMENTAL DEVELOPMENT
- This is incremental progress in an ongoing development process, not a final submission
- Monitor how the solution is evolving with each update
- Assess the overall direction and approach the candidate is taking
- Remember: The candidate is still actively developing - the solution may be incomplete
- If the current state appears substantially complete or near completion:
  * You may provide constructive feedback on the current progress
  * Consider asking thoughtful follow-up questions about their approach
  * Explore edge cases or optimizations if appropriate
- If the solution is still in active development (most likely):
  * Continue observing the iterative development process
  * Allow natural progression of their problem-solving
  * Only intervene if critical issues might derail their progress
  * Do not provide feedback unless the solution seems nearly complete or has critical issues

This message is only for you reference and you dont need to emit any response as part of that. 

**Decision Point:** Based on the current code state and overall solution progress, determine if this warrants active engagement or continued observation of the ongoing development process.
"""
        
        logger.info("Built LLM prompt", 
                   is_first_submission=diff_result.is_first_submission,
                   has_diff=bool(diff_result.diff_content),
                   prompt_length=len(prompt))
        
        # Add solution completeness indicators
        completeness_indicators = self._get_completeness_indicators(diff_result.current_code, language)
        if completeness_indicators:
            prompt += f"""

**Solution Completeness Indicators:**
{completeness_indicators}
"""
        
        return prompt.strip()
    
    def _get_completeness_indicators(self, code_content: str, language: str) -> str:
        """
        Analyze code to provide indicators of solution completeness.
        
        Args:
            code_content: The code to analyze
            language: Programming language
            
        Returns:
            String with completeness indicators
        """
        indicators = []
        code_lower = code_content.lower()
        lines = code_content.strip().split('\n')
        non_empty_lines = [line for line in lines if line.strip()]
        
        # Basic structure indicators
        if len(non_empty_lines) > 3:
            indicators.append("✅ Has substantial code structure")
        else:
            indicators.append("⚠️ Minimal code structure")
        
        # Language-specific patterns
        if language.lower() in ['javascript', 'typescript']:
            if 'function' in code_lower or '=>' in code_content:
                indicators.append("✅ Contains function definition")
            if 'return' in code_lower:
                indicators.append("✅ Has return statement")
        elif language.lower() == 'python':
            if 'def ' in code_content:
                indicators.append("✅ Contains function definition")
            if 'return' in code_lower:
                indicators.append("✅ Has return statement")
        elif language.lower() == 'java':
            if 'public' in code_lower and 'static' in code_lower:
                indicators.append("✅ Contains method definition")
            if 'return' in code_lower:
                indicators.append("✅ Has return statement")
        
        # Common completeness patterns
        if any(keyword in code_lower for keyword in ['if', 'else', 'for', 'while']):
            indicators.append("✅ Contains control flow logic")
        
        if any(keyword in code_lower for keyword in ['todo', 'fixme', '// your code', 'your code goes here']):
            indicators.append("⚠️ Contains placeholder comments")
        
        # Comments and documentation
        comment_patterns = ['//', '/*', '#', '"""', "'''"]
        if any(pattern in code_content for pattern in comment_patterns):
            indicators.append("✅ Contains comments/documentation")
        
        # Estimate completeness level
        if len(indicators) >= 4 and not any("⚠️" in ind for ind in indicators):
            indicators.append("🎯 **APPEARS SUBSTANTIALLY COMPLETE** - Consider active engagement")
        elif len(indicators) >= 3:
            indicators.append("🔄 **MODERATE PROGRESS** - Continue monitoring")
        else:
            indicators.append("🚧 **EARLY STAGE** - Allow continued development")
        
        return '\n'.join(f"- {indicator}" for indicator in indicators)
    
    async def _print_diff_results(self, diff_result: DiffResult):
        """Print diff results for debugging/monitoring."""
        print(f"\n{'='*50}")
        print(f"CODE DIFF RESULTS")
        print(f"{'='*50}")
        print(f"Question ID: {diff_result.question_id}")
        print(f"Solution ID: {diff_result.solution_id}")
        print(f"Timestamp: {diff_result.timestamp}")
        print(f"Has Changes: {diff_result.has_changes}")
        print(f"Is First Submission: {diff_result.is_first_submission}")
        
        if diff_result.diff_content:
            print(f"\nDIFF CONTENT:")
            print(f"{'-'*30}")
            print(diff_result.diff_content)
            print(f"{'-'*30}")
        else:
            if diff_result.is_first_submission:
                print("\nFirst submission - no diff to show")
            else:
                print("\nNo changes detected")
        
        print(f"{'='*50}\n")
        
        # Also log for structured logging
        logger.info("Diff processing completed",
                   question_id=diff_result.question_id,
                   solution_id=diff_result.solution_id,
                   has_changes=diff_result.has_changes,
                   is_first_submission=diff_result.is_first_submission)
        
    def _extract_code_snippets(self, message: str) -> list:
        """Extract code snippets from a message.
        
        Args:
            message: Message to extract code from
            
        Returns:
            List of code snippets found
        """
        # Simple code detection - look for common patterns
        code_patterns = [
            "```",  # Markdown code blocks
            "`",    # Inline code
            "def ", # Python function
            "class ", # Python class
            "function ", # JavaScript function
            "public ", # Java/C# method
            "import ", # Import statements
            "from ",   # From statements
        ]
        
        code_snippets = []
        lines = message.split('\n')
        
        for line in lines:
            line = line.strip()
            if any(pattern in line for pattern in code_patterns):
                code_snippets.append(line)
                
        return code_snippets
        
    def _detect_language(self, message: str) -> str:
        """Detect programming language from message.
        
        Args:
            message: Message to analyze
            
        Returns:
            Detected programming language
        """
        # Simple language detection based on keywords
        language_keywords = {
            "python": ["def ", "class ", "import ", "from ", "if __name__", "self.", "print("],
            "javascript": ["function ", "const ", "let ", "var ", "console.log", "=>", "async "],
            "java": ["public ", "private ", "class ", "static ", "void ", "String ", "int "],
            "cpp": ["#include", "using namespace", "std::", "cout <<", "cin >>"],
            "csharp": ["using ", "namespace ", "public ", "private ", "Console.WriteLine"],
        }
        
        message_lower = message.lower()
        
        for language, keywords in language_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                return language
                
        return "unknown"
        
    def _add_code_snippet(self, code_snippets: list, language: str):
        """Add code snippets to context.
        
        Args:
            code_snippets: List of code snippets to add
            language: Programming language of the snippets
        """
        for snippet in code_snippets:
            self.code_snippets.append({
                "code": snippet,
                "language": language,
                "timestamp": "now"  # In real implementation, use actual timestamp
            })
            
        # Keep only the last max_code_snippets
        if len(self.code_snippets) > self.max_code_snippets:
            self.code_snippets = self.code_snippets[-self.max_code_snippets:]
            
    def get_code_context(self) -> list:
        """Get the current code context.
        
        Returns:
            List of code snippets in context
        """
        return self.code_snippets.copy()
        
    def clear_code_context(self):
        """Clear all code snippets from context."""
        self.code_snippets.clear()
        
    def get_status(self) -> dict:
        """Get the current status of the code context processor.
        
        Returns:
            Dictionary containing code context processor status
        """
        return {
            "type": "code_context",
            "code_snippets_count": len(self.code_snippets),
            "max_code_snippets": self.max_code_snippets,
            "language_detection": self.language_detection,
            "languages_found": list(set(snippet["language"] for snippet in self.code_snippets))
        }
