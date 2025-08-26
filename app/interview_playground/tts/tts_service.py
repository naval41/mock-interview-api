"""
TTS service for creating and managing TTS implementations.
"""

from app.interview_playground.tts.base_tts import BaseTTS
from app.interview_playground.tts.deepgram_tts import DeepgramTTS


class TTSService:
    """Service for creating TTS implementations."""
    
    def __init__(self, provider: str = "deepgram", **kwargs):
        """Initialize TTS service.
        
        Args:
            provider: TTS provider name
            **kwargs: Provider-specific arguments
        """
        self.provider = provider
        self.kwargs = kwargs
        self._tts_instance = None
        
    def create_deepgram(self, api_key: str, voice: str = "aura-2-andromeda-en") -> BaseTTS:
        """Create a Deepgram TTS instance.
        
        Args:
            api_key: Deepgram API key
            voice: Voice name for synthesis
            
        Returns:
            DeepgramTTS instance
        """
        return DeepgramTTS(api_key=api_key, voice=voice)
        
    def create(self, provider: str, **kwargs) -> BaseTTS:
        """Create a TTS instance based on provider.
        
        Args:
            provider: TTS provider name
            **kwargs: Provider-specific arguments
            
        Returns:
            BaseTTS instance
        """
        if provider.lower() == "deepgram":
            api_key = kwargs.get("api_key", "")
            voice = kwargs.get("voice", "aura-2-andromeda-en")
            return self.create_deepgram(api_key, voice)
        else:
            raise ValueError(f"Unknown TTS provider: {provider}")
            
    def setup_processor(self):
        """Setup the TTS processor based on configured provider.
        
        Returns:
            FrameProcessor instance
        """
        if not self._tts_instance:
            if self.provider.lower() == "deepgram":
                api_key = self.kwargs.get("api_key", "")
                voice = self.kwargs.get("voice", "aura-2-andromeda-en")
                self._tts_instance = self.create_deepgram(api_key, voice)
            else:
                raise ValueError(f"Unknown TTS provider: {self.provider}")
                
        return self._tts_instance.setup_processor()

