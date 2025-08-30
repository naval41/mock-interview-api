"""
Processors package for interview playground.
Provides simple abstraction for different processor types.
"""

from .base_processor import BaseProcessor
from .code_context_processor import CodeContextProcessor
from .design_context_processor import DesignContextProcessor
from .processors_service import ProcessorsService

__all__ = [
    "BaseProcessor",
    "CodeContextProcessor",
    "DesignContextProcessor",
    "ProcessorsService"
]
