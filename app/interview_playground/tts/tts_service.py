"""
TTS service for creating and managing TTS implementations.
"""

from app.interview_playground.tts.base_tts import BaseTTS
from app.interview_playground.tts.deepgram_tts import DeepgramTTS
from app.interview_playground.tts.kokoro_tts import KokoroTTS


class TTSService:
    """Service for creating TTS implementations."""

    def __init__(self, provider: str = "kokoro", **kwargs):
        """Initialize TTS service.

        Args:
            provider: TTS provider name ("kokoro", "deepgram")
            **kwargs: Provider-specific arguments
        """
        self.provider = provider
        self.kwargs = kwargs
        self._tts_instance = None

    def create_deepgram(self, api_key: str, voice: str = "aura-2-vesta-en",
                       filter_code: bool = True, filter_tables: bool = True,
                       enable_markdown_filter: bool = True) -> BaseTTS:
        """Create a Deepgram TTS instance with markdown filtering."""
        return DeepgramTTS(
            api_key=api_key,
            voice=voice,
            filter_code=filter_code,
            filter_tables=filter_tables,
            enable_markdown_filter=enable_markdown_filter
        )

    def create_kokoro(self, voice: str = "af_heart", speed: float = 1.0,
                     lang_code: str = "a", filter_code: bool = True,
                     filter_tables: bool = True,
                     enable_markdown_filter: bool = True) -> BaseTTS:
        """Create a Kokoro TTS instance (local, no API key needed)."""
        return KokoroTTS(
            voice=voice,
            speed=speed,
            lang_code=lang_code,
            filter_code=filter_code,
            filter_tables=filter_tables,
            enable_markdown_filter=enable_markdown_filter,
        )

    def create(self, provider: str, **kwargs) -> BaseTTS:
        """Create a TTS instance based on provider."""
        if provider.lower() == "deepgram":
            return self.create_deepgram(
                api_key=kwargs.get("api_key", ""),
                voice=kwargs.get("voice", "aura-2-vesta-en"),
                filter_code=kwargs.get("filter_code", True),
                filter_tables=kwargs.get("filter_tables", True),
                enable_markdown_filter=kwargs.get("enable_markdown_filter", True),
            )
        elif provider.lower() == "kokoro":
            return self.create_kokoro(
                voice=kwargs.get("voice", "af_heart"),
                speed=kwargs.get("speed", 1.0),
                lang_code=kwargs.get("lang_code", "a"),
                filter_code=kwargs.get("filter_code", True),
                filter_tables=kwargs.get("filter_tables", True),
                enable_markdown_filter=kwargs.get("enable_markdown_filter", True),
            )
        else:
            raise ValueError(f"Unknown TTS provider: {provider}")

    def setup_processor(self):
        """Setup the TTS processor based on configured provider.

        Returns:
            FrameProcessor instance
        """
        if not self._tts_instance:
            if self.provider.lower() == "deepgram":
                self._tts_instance = self.create_deepgram(
                    api_key=self.kwargs.get("api_key", ""),
                    voice=self.kwargs.get("voice", "aura-2-vesta-en"),
                    filter_code=self.kwargs.get("filter_code", True),
                    filter_tables=self.kwargs.get("filter_tables", True),
                    enable_markdown_filter=self.kwargs.get("enable_markdown_filter", True),
                )
            elif self.provider.lower() == "kokoro":
                self._tts_instance = self.create_kokoro(
                    voice=self.kwargs.get("voice", "af_heart"),
                    speed=self.kwargs.get("speed", 1.0),
                    lang_code=self.kwargs.get("lang_code", "a"),
                    filter_code=self.kwargs.get("filter_code", True),
                    filter_tables=self.kwargs.get("filter_tables", True),
                    enable_markdown_filter=self.kwargs.get("enable_markdown_filter", True),
                )
            else:
                raise ValueError(f"Unknown TTS provider: {self.provider}")

        return self._tts_instance.setup_processor()

