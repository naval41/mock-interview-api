"""
Excalidraw JSON Parser - A Python library for parsing Excalidraw diagrams into text descriptions.

This package provides tools for parsing Excalidraw JSON exports and converting them into
human-readable text descriptions. It handles element parsing, relationship analysis,
and natural language generation.

Example:
    >>> from excalidraw_parser import ExcalidrawParser
    >>> parser = ExcalidrawParser()
    >>> description = parser.parse(excalidraw_json)
    >>> print(description)
"""

from typing import List

from .parser import ExcalidrawParser
from .models import (
    BaseElement, RectangleElement, TextElement, ArrowElement, ElementBinding,
    Component, Connection, DiagramStructure
)
from .exceptions import ExcalidrawParserError, JSONParseError, ValidationError, ElementProcessingError
from .factory import ElementFactory
from .analyzer import RelationshipAnalyzer
from .description_generator import DescriptionGenerator
from .output_generator import (
    OutputGenerator, OutputFormat, OutputConfig, OutputGenerationError,
    get_output_factory, register_output_generator
)
from .mermaid_generator import MermaidGenerator
from .diagram_type_detector import DiagramTypeDetector, DiagramType

# Register the output generators
register_output_generator(OutputFormat.DESCRIPTION, DescriptionGenerator)
register_output_generator(OutputFormat.MERMAID, MermaidGenerator)

__version__: str = "0.1.0"
__author__: str = "Developer"
__email__: str = "developer@example.com"

__all__: List[str] = [
    # Main classes
    "ExcalidrawParser",
    "ElementFactory", 
    "RelationshipAnalyzer",
    "DescriptionGenerator",
    "OutputGenerator",
    "MermaidGenerator",
    "DiagramTypeDetector",
    
    # Output formats
    "OutputFormat",
    "register_output_generator",
    
    # Diagram types
    "DiagramType",
    
    # Data models
    "BaseElement",
    "RectangleElement",
    "TextElement", 
    "ArrowElement",
    "ElementBinding",
    "Component",
    "Connection",
    "DiagramStructure",
    
    # Exceptions
    "ExcalidrawParserError",
    "JSONParseError",
    "ValidationError",
    "ElementProcessingError",
]

