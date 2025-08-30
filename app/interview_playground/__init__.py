"""
Interview Playground Package

A comprehensive package for building interview bots with:
- STT (Speech-to-Text) processing with simple provider abstraction
- TTS (Text-to-Speech) synthesis with simple provider abstraction
- LLM (Large Language Model) processing with simple provider abstraction
- Transport with simple provider abstraction
- Processors with simple provider abstraction
- Interview pipeline management
- Bot orchestration
"""

from .stt import BaseSTT, DeepgramSTT, STTService
from .tts import BaseTTS, DeepgramTTS, TTSService as TTSServiceClass
from .llm import BaseLLM, GoogleLLM, OpenAILLM, LLMService
from .transport import BaseTransport, WebRTCTransport, TransportService
from .processors import BaseProcessor, CodeContextProcessor, DesignContextProcessor, ProcessorsService
from .interview_bot import InterviewBot
from .pipeline.interview_pipeline import InterviewPipeline

__version__ = "1.0.0"

__all__ = [
    "BaseSTT",
    "DeepgramSTT", 
    "STTService",
    "BaseTTS",
    "DeepgramTTS",
    "TTSServiceClass",
    "BaseLLM",
    "GoogleLLM",
    "OpenAILLM",
    "LLMService",
    "BaseTransport",
    "WebRTCTransport",
    "TransportService",
    "BaseProcessor",
    "CodeContextProcessor",
    "DesignContextProcessor",
    "ProcessorsService",
    "InterviewBot",
    "InterviewPipeline"
]
