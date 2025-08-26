"""
Interview Playground Package

A comprehensive package for building interview bots with:
- STT (Speech-to-Text) processing with simple provider abstraction
- TTS (Text-to-Speech) synthesis
- Interview pipeline management
- Bot orchestration
"""

from .stt import BaseSTT, DeepgramSTT, STTService
from .interview_bot import InterviewBot
from .pipeline.interview_pipeline import InterviewPipeline

__version__ = "1.0.0"

__all__ = [
    "BaseSTT",
    "DeepgramSTT", 
    "STTService",
    "InterviewBot",
    "InterviewPipeline"
]
