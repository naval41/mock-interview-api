"""
ElevenLabs TTS implementation that extends BaseTTS with MarkdownTextFilter support.
"""

from pipecat.processors.frame_processor import FrameProcessor
from app.interview_playground.tts.base_tts import BaseTTS
from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
from pipecat.utils.text.markdown_text_filter import MarkdownTextFilter


class ElevenLabsTTS(BaseTTS):
    """ElevenLabs TTS implementation with markdown filtering."""

    def __init__(
        self,
        api_key: str,
        voice_id: str = "JBFqnCBsd6RMkjVDRZzb",
        model: str = "eleven_turbo_v2_5",
        filter_code: bool = True,
        filter_tables: bool = True,
        enable_markdown_filter: bool = True,
    ):
        self.api_key = api_key
        self.voice_id = voice_id
        self.model = model
        self.filter_code = filter_code
        self.filter_tables = filter_tables
        self.enable_markdown_filter = enable_markdown_filter

    def setup_processor(self) -> FrameProcessor:
        """Setup the ElevenLabs TTS FrameProcessor instance with MarkdownTextFilter."""
        text_filters = []
        if self.enable_markdown_filter:
            text_filters.append(
                MarkdownTextFilter(
                    params=MarkdownTextFilter.InputParams(
                        enable_text_filter=True,
                        filter_code=self.filter_code,
                        filter_tables=self.filter_tables,
                    )
                )
            )

        kwargs = {
            "api_key": self.api_key,
            "voice_id": self.voice_id,
            "model": self.model,
        }

        if text_filters:
            kwargs["text_filters"] = text_filters

        return ElevenLabsTTSService(**kwargs)
