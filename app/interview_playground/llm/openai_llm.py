"""
OpenAI LLM implementation that extends BaseLLM.
"""

from pipecat.processors.frame_processor import FrameProcessor
from app.interview_playground.llm.base_llm import BaseLLM


class OpenAILLM(BaseLLM):
    """OpenAI LLM implementation."""
    
    def __init__(self, api_key: str, model: str = "gpt-4"):
        """Initialize OpenAI LLM.
        
        Args:
            api_key: OpenAI API key
            model: Model name for generation
        """
        self.api_key = api_key
        self.model = model
        
    def setup_processor(self) -> FrameProcessor:
        """Setup the OpenAI LLM FrameProcessor instance.
        
        Returns:
            FrameProcessor configured for OpenAI LLM
        """
        # For now, return a simple FrameProcessor
        # In real implementation, this would return an OpenAI-specific processor
        from pipecat.processors.frame_processor import FrameProcessor
        
        processor = FrameProcessor(name="openai_llm")
        # Here you would configure the processor with OpenAI-specific settings
        # processor.api_key = self.api_key
        # processor.model = self.model
        
        return processor
