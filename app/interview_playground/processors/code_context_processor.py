"""
Code Context Processor implementation that extends BaseProcessor.
"""

from pipecat.processors.frame_processor import FrameProcessor
from app.interview_playground.processors.base_processor import BaseProcessor


class CodeContextProcessor(BaseProcessor):
    """Code Context Processor for handling code-related messages and context."""
    
    def __init__(self, max_code_snippets: int = 10, language_detection: bool = True):
        """Initialize Code Context Processor.
        
        Args:
            max_code_snippets: Maximum number of code snippets to keep in context
            language_detection: Whether to automatically detect programming language
        """
        self.max_code_snippets = max_code_snippets
        self.language_detection = language_detection
        self.code_snippets = []
        self.language_context = {}
        
    def setup_processor(self) -> FrameProcessor:
        """Setup the Code Context Processor FrameProcessor instance.
        
        Returns:
            FrameProcessor configured for code context processing
        """
        # For now, return a simple FrameProcessor
        # In real implementation, this would return a code-specific processor
        from pipecat.processors.frame_processor import FrameProcessor
        
        processor = FrameProcessor(name="code_context_processor")
        # Here you would configure the processor with code-specific settings
        
        return processor
        
    async def process_message(self, message: str) -> dict:
        """Process a code-related message and return the result.
        
        Args:
            message: Message to process (could contain code snippets)
            
        Returns:
            Dictionary containing processed result
        """
        # Detect if message contains code
        code_snippets = self._extract_code_snippets(message)
        language = self._detect_language(message) if self.language_detection else "unknown"
        
        # Store code snippet if found
        if code_snippets:
            self._add_code_snippet(code_snippets, language)
            
        # Process the message for code context
        processed_result = {
            "type": "code_context",
            "original_message": message,
            "code_snippets": code_snippets,
            "language": language,
            "context_size": len(self.code_snippets),
            "processed": True
        }
        
        return processed_result
        
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
