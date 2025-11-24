"""
Processors service for creating and managing processor implementations.
"""

from app.interview_playground.processors.base_processor import BaseProcessor
from app.interview_playground.processors.code_context_processor import CodeContextProcessor
from app.interview_playground.processors.design_context_processor import DesignContextProcessor


class ProcessorsService:
    """Service for creating processor implementations and processing messages."""
    
    def __init__(self, code_context: bool = True, design_context: bool = True, **kwargs):
        """Initialize Processors service.
        
        Args:
            code_context: Whether to enable code context processing
            design_context: Whether to enable design context processing
            **kwargs: Additional processor-specific arguments
        """
        self.code_context = code_context
        self.design_context = design_context
        self.kwargs = kwargs
        self._processors = {}
        self._initialized = False
        
    def setup_processors(self) -> list:
        """Setup and return all configured processors.
        
        Returns:
            List of configured processors
        """
        processors = []
        
        if self.code_context:
            code_kwargs = {
                "max_code_snippets": self.kwargs.get("max_code_snippets", 10),
                "language_detection": self.kwargs.get("language_detection", True),
                "debounce_seconds": self.kwargs.get("debounce_seconds", 30)
            }
            code_context_processor = CodeContextProcessor(**code_kwargs)
            # Store the processor instance directly (it's now a FrameProcessor)
            self._processors["code"] = code_context_processor
            processors.append(code_context_processor)
            
        if self.design_context:
            design_kwargs = {
                "max_design_elements": self.kwargs.get("max_design_elements", 15),
                "design_patterns": self.kwargs.get("design_patterns", True)
            }
            design_context_processor = DesignContextProcessor(**design_kwargs)
            # Store the processor instance directly (it's now a FrameProcessor)
            self._processors["design"] = design_context_processor
            processors.append(design_context_processor)
            
        self._initialized = True
        return processors
        
    async def process_message(self, message: str, context_type: str = "auto") -> dict:
        """Process a message through appropriate processors and return the result.
        
        Args:
            message: Message to process
            context_type: Type of context to process ("code", "design", or "auto")
            
        Returns:
            Dictionary containing processed results from all applicable processors
        """
        if not self._initialized:
            self.setup_processors()
            
        results = {
            "original_message": message,
            "context_type": context_type,
            "processed_results": {},
            "total_processors": len(self._processors)
        }
        
        # Process message through appropriate processors
        if context_type == "auto":
            # Process through all enabled processors
            for processor_name, processor in self._processors.items():
                try:
                    result = await processor.process_message(message)
                    results["processed_results"][processor_name] = result
                except Exception as e:
                    results["processed_results"][processor_name] = {
                        "error": str(e),
                        "processed": False
                    }
                    
        elif context_type == "code" and "code" in self._processors:
            # Process only through code processor
            try:
                result = await self._processors["code"].process_message(message)
                results["processed_results"]["code"] = result
            except Exception as e:
                results["processed_results"]["code"] = {
                    "error": str(e),
                    "processed": False
                }
                
        elif context_type == "design" and "design" in self._processors:
            # Process only through design processor
            try:
                result = await self._processors["design"].process_message(message)
                results["processed_results"]["design"] = result
            except Exception as e:
                results["processed_results"]["design"] = {
                    "error": str(e),
                    "processed": False
                }
                
        else:
            results["error"] = f"Unknown context type: {context_type}"
            
        return results
        
    def get_processor(self, processor_type: str) -> BaseProcessor:
        """Get a specific processor by type.
        
        Args:
            processor_type: Type of processor ("code" or "design")
            
        Returns:
            The requested processor instance
        """
        if not self._initialized:
            self.setup_processors()
            
        return self._processors.get(processor_type)
        
    def get_all_processors(self) -> dict:
        """Get all configured processors.
        
        Returns:
            Dictionary of all processors by type
        """
        if not self._initialized:
            self.setup_processors()
            
        return self._processors.copy()
        
    def get_processor_status(self) -> dict:
        """Get status of all processors.
        
        Returns:
            Dictionary containing status of all processors
        """
        if not self._initialized:
            self.setup_processors()
            
        status = {
            "code_context_enabled": self.code_context,
            "design_context_enabled": self.design_context,
            "total_processors": len(self._processors),
            "processors": {}
        }
        
        for processor_name, processor in self._processors.items():
            status["processors"][processor_name] = processor.get_status()
            
        return status
        
    def clear_all_contexts(self):
        """Clear all contexts from all processors."""
        if not self._initialized:
            return
            
        for processor in self._processors.values():
            if hasattr(processor, 'clear_code_context'):
                processor.clear_code_context()
            if hasattr(processor, 'clear_design_context'):
                processor.clear_design_context()
                
    def get_combined_context(self) -> dict:
        """Get combined context from all processors.
        
        Returns:
            Dictionary containing combined context from all processors
        """
        if not self._initialized:
            self.setup_processors()
            
        combined_context = {}
        
        if "code" in self._processors:
            combined_context["code"] = self._processors["code"].get_code_context()
            
        if "design" in self._processors:
            combined_context["design"] = self._processors["design"].get_design_context()
            
        return combined_context
