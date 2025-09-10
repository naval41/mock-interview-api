"""
Deepgram TTS implementation that extends BaseTTS with MarkdownTextFilter support.
"""

from pipecat.processors.frame_processor import FrameProcessor
from app.interview_playground.tts.base_tts import BaseTTS
from pipecat.services.deepgram.tts import DeepgramTTSService
from pipecat.utils.text.markdown_text_filter import MarkdownTextFilter


class DeepgramTTS(BaseTTS):
    """Deepgram TTS implementation with markdown filtering."""
    
    def __init__(self, api_key: str, voice: str = "aura-2-andromeda-en", 
                 filter_code: bool = True, filter_tables: bool = True, 
                 enable_markdown_filter: bool = True):
        """Initialize Deepgram TTS with markdown filtering.
        
        Args:
            api_key: Deepgram API key
            voice: Voice name for synthesis
            filter_code: Whether to remove code blocks from TTS output
            filter_tables: Whether to remove Markdown tables from TTS output
            enable_markdown_filter: Whether to enable markdown filtering
        """
        self.api_key = api_key
        self.voice = voice
        self.filter_code = filter_code
        self.filter_tables = filter_tables
        self.enable_markdown_filter = enable_markdown_filter
        
    def setup_processor(self) -> FrameProcessor:
        """Setup the Deepgram TTS FrameProcessor instance with MarkdownTextFilter.
        
        Returns:
            FrameProcessor configured for Deepgram TTS with markdown filtering
        """
        # Create markdown filter with custom configuration
        markdown_filter = None
        if self.enable_markdown_filter:
            markdown_filter = MarkdownTextFilter(
                params=MarkdownTextFilter.InputParams(
                    enable_text_filter=True,
                    filter_code=self.filter_code,
                    filter_tables=self.filter_tables
                )
            )
        
        # Create Deepgram TTS service with markdown filter
        return DeepgramTTSService(
            api_key=self.api_key,
            voice=self.voice,
            text_filter=markdown_filter
        )