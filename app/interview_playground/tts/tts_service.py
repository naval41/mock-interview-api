"""
TTS service for creating and managing TTS implementations.
"""

from app.interview_playground.tts.base_tts import BaseTTS
from app.interview_playground.tts.deepgram_tts import DeepgramTTS
from app.interview_playground.tts.elevenlabs_tts import ElevenLabsTTS


class TTSService:
    """Service for creating TTS implementations."""

    def __init__(self, provider: str = "deepgram", **kwargs):
        self.provider = provider
        self.kwargs = kwargs
        self._tts_instance = None

    def create_deepgram(self, api_key: str, voice: str = "aura-2-vesta-en",
                       filter_code: bool = True, filter_tables: bool = True,
                       enable_markdown_filter: bool = True) -> BaseTTS:
        return DeepgramTTS(
            api_key=api_key,
            voice=voice,
            filter_code=filter_code,
            filter_tables=filter_tables,
            enable_markdown_filter=enable_markdown_filter,
        )

    def create_elevenlabs(self, api_key: str, voice_id: str = "JBFqnCBsd6RMkjVDRZzb",
                          model: str = "eleven_turbo_v2_5",
                          filter_code: bool = True, filter_tables: bool = True,
                          enable_markdown_filter: bool = True) -> BaseTTS:
        return ElevenLabsTTS(
            api_key=api_key,
            voice_id=voice_id,
            model=model,
            filter_code=filter_code,
            filter_tables=filter_tables,
            enable_markdown_filter=enable_markdown_filter,
        )

    def setup_processor(self):
        if not self._tts_instance:
            provider = self.provider.lower()
            if provider == "deepgram":
                api_key = self.kwargs.get("api_key", "")
                voice = self.kwargs.get("voice", "aura-2-vesta-en")
                filter_code = self.kwargs.get("filter_code", True)
                filter_tables = self.kwargs.get("filter_tables", True)
                enable_markdown_filter = self.kwargs.get("enable_markdown_filter", True)
                self._tts_instance = self.create_deepgram(
                    api_key, voice, filter_code, filter_tables, enable_markdown_filter
                )
            elif provider == "elevenlabs":
                api_key = self.kwargs.get("api_key", "")
                voice_id = self.kwargs.get("voice_id", "9PvnT6XRzlljoaDG6Knu")
                model = self.kwargs.get("model", "eleven_turbo_v2_5")
                filter_code = self.kwargs.get("filter_code", True)
                filter_tables = self.kwargs.get("filter_tables", True)
                enable_markdown_filter = self.kwargs.get("enable_markdown_filter", True)
                self._tts_instance = self.create_elevenlabs(
                    api_key, voice_id, model, filter_code, filter_tables, enable_markdown_filter
                )
            else:
                raise ValueError(f"Unknown TTS provider: {self.provider}")

        return self._tts_instance.setup_processor()
