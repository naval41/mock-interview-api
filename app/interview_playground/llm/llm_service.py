"""
LLM service for creating and managing LLM implementations.
"""

from app.interview_playground.llm.base_llm import BaseLLM
from app.interview_playground.llm.google_llm import GoogleLLM
from app.interview_playground.llm.openai_llm import OpenAILLM


class LLMService:
    """Service for creating LLM implementations."""
    
    def __init__(self, provider: str = "google", **kwargs):
        """Initialize LLM service.
        
        Args:
            provider: LLM provider name
            **kwargs: Provider-specific arguments
        """
        self.provider = provider
        self.kwargs = kwargs
        self._llm_instance = None
        
    def create_google(self, api_key: str, model: str = "gemini-2.0-flash", custom_instructions: str = None) -> BaseLLM:
        """Create a Google LLM instance.
        
        Args:
            api_key: Google API key
            model: Model name for generation
            custom_instructions: Optional custom system instructions
            
        Returns:
            GoogleLLM instance
        """
        return GoogleLLM(api_key=api_key, model=model, custom_instructions=custom_instructions)
        
    def create_openai(self, api_key: str, model: str = "gpt-4") -> BaseLLM:
        """Create an OpenAI LLM instance.
        
        Args:
            api_key: OpenAI API key
            model: Model name for generation
            
        Returns:
            OpenAILLM instance
        """
        return OpenAILLM(api_key=api_key, model=model)
        
    def create(self, provider: str, **kwargs) -> BaseLLM:
        """Create an LLM instance based on provider.
        
        Args:
            provider: LLM provider name
            **kwargs: Provider-specific arguments
            
        Returns:
            BaseLLM instance
        """
        if provider.lower() == "google":
            api_key = kwargs.get("api_key", "")
            model = kwargs.get("model", "gemini-2.0-flash")
            custom_instructions = kwargs.get("custom_instructions")
            return self.create_google(api_key, model, custom_instructions)
        elif provider.lower() == "openai":
            api_key = kwargs.get("api_key", "")
            model = kwargs.get("model", "gpt-4")
            return self.create_openai(api_key, model)
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")
            
    def setup_processor(self):
        """Setup the LLM processor based on configured provider.
        
        Returns:
            FrameProcessor instance
        """
        if not self._llm_instance:
            if self.provider.lower() == "google":
                api_key = self.kwargs.get("api_key", "")
                model = self.kwargs.get("model", "gemini-2.0-flash")
                custom_instructions = self.kwargs.get("custom_instructions")
                self._llm_instance = self.create_google(api_key, model, custom_instructions)
            elif self.provider.lower() == "openai":
                api_key = self.kwargs.get("api_key", "")
                model = self.kwargs.get("model", "gpt-4")
                self._llm_instance = self.create_openai(api_key, model)
            else:
                raise ValueError(f"Unknown LLM provider: {self.provider}")
                
        return self._llm_instance.setup_processor()
