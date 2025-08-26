"""
TTS (Text-to-Speech) package for interview playground.
Provides simple abstraction for different TTS providers.
"""

from .base_tts import BaseTTS
from .deepgram_tts import DeepgramTTS
from .tts_service import TTSService

__all__ = [
    "BaseTTS",
    "DeepgramTTS", 
    "TTSService"
]

