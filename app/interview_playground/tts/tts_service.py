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
        
    def create_deepgram(self, api_key: str, voice: str = "aura-2-andromeda-en", 
                       filter_code: bool = True, filter_tables: bool = True, 
                       enable_markdown_filter: bool = True) -> BaseTTS:
        """Create a Deepgram TTS instance with markdown filtering.
        
        Args:
            api_key: Deepgram API key
            voice: Voice name for synthesis
            filter_code: Whether to remove code blocks from TTS output
            filter_tables: Whether to remove Markdown tables from TTS output
            enable_markdown_filter: Whether to enable markdown filtering
            
        Returns:
            DeepgramTTS instance with markdown filtering
        """
        return DeepgramTTS(
            api_key=api_key, 
            voice=voice,
            filter_code=filter_code,
            filter_tables=filter_tables,
            enable_markdown_filter=enable_markdown_filter
        )
        
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
            filter_code = kwargs.get("filter_code", True)
            filter_tables = kwargs.get("filter_tables", True)
            enable_markdown_filter = kwargs.get("enable_markdown_filter", True)
            return self.create_deepgram(api_key, voice, filter_code, filter_tables, enable_markdown_filter)
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
                filter_code = self.kwargs.get("filter_code", True)
                filter_tables = self.kwargs.get("filter_tables", True)
                enable_markdown_filter = self.kwargs.get("enable_markdown_filter", True)
                self._tts_instance = self.create_deepgram(api_key, voice, filter_code, filter_tables, enable_markdown_filter)
            else:
                raise ValueError(f"Unknown TTS provider: {self.provider}")
                
        return self._tts_instance.setup_processor()

