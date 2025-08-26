"""
STT service for creating and managing STT implementations.
"""

from app.interview_playground.stt.base_stt import BaseSTT
from app.interview_playground.stt.deepgram_stt import DeepgramSTT


class STTService:
    """Service for creating and managing STT implementations."""
    
    def __init__(self, provider: str = "deepgram", **kwargs):
        """Initialize STT service.
        
        Args:
            provider: STT provider name
            **kwargs: Provider-specific arguments
        """
        self.provider = provider
        self.kwargs = kwargs
        self._stt_instance = None
        
    def create_deepgram(self, api_key: str, language: str = "en") -> BaseSTT:
        """Create a Deepgram STT instance.
        
        Args:
            api_key: Deepgram API key
            language: Language code for transcription
            
        Returns:
            DeepgramSTT instance
        """
        return DeepgramSTT(api_key=api_key, language=language)
        
    def create(self, provider: str, **kwargs) -> BaseSTT:
        """Create an STT instance based on provider.
        
        Args:
            provider: STT provider name
            **kwargs: Provider-specific arguments
            
        Returns:
            BaseSTT instance
        """
        if provider.lower() == "deepgram":
            api_key = kwargs.get("api_key", "")
            language = kwargs.get("language", "en")
            return self.create_deepgram(api_key, language)
        else:
            raise ValueError(f"Unknown STT provider: {provider}")
            
    def setup_processor(self):
        """Setup the STT processor based on configured provider.
        
        Returns:
            FrameProcessor instance
        """
        if not self._stt_instance:
            if self.provider.lower() == "deepgram":
                api_key = self.kwargs.get("api_key", "")
                language = self.kwargs.get("language", "en")
                self._stt_instance = self.create_deepgram(api_key, language)
            else:
                raise ValueError(f"Unknown STT provider: {self.provider}")
                
        return self._stt_instance.setup_processor()
