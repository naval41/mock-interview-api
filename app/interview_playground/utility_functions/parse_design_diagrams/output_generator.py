"""Base classes and interfaces for output generation.

This module provides the abstract base classes and interfaces for generating
different types of output from parsed Excalidraw diagrams. It supports multiple
output formats while maintaining a consistent interface.

Classes:
    OutputGenerator: Abstract base class for all output generators
    OutputFormat: Enum defining supported output formats
    OutputConfig: Configuration class for output generation
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass

from .models import DiagramStructure


class OutputFormat(Enum):
    """Enumeration of supported output formats."""
    DESCRIPTION = "description"  # Natural language description
    MERMAID = "mermaid"         # Mermaid diagram syntax
    # Future formats can be added here:
    # PLANTUML = "plantuml"
    # GRAPHVIZ = "graphviz"


@dataclass
class OutputConfig:
    """Configuration for output generation.
    
    This class holds configuration options that are common across different
    output formats, as well as format-specific options.
    
    Attributes:
        format_style: Style of output (standard, detailed, concise, technical)
        include_positions: Whether to include position information
        max_connections_detail: Maximum connections to describe in detail
        custom_options: Format-specific custom options
    """
    format_style: str = "standard"
    include_positions: bool = False
    max_connections_detail: int = 10
    custom_options: Dict[str, Any] = None
    
    def __post_init__(self):
        """Initialize custom_options if not provided."""
        if self.custom_options is None:
            self.custom_options = {}


class OutputGenerator(ABC):
    """Abstract base class for all output generators.
    
    This class defines the interface that all output generators must implement.
    It provides a consistent way to generate different types of output from
    parsed Excalidraw diagram structures.
    
    The generator pattern allows for:
    - Multiple output formats from the same parsed structure
    - Consistent configuration and error handling
    - Easy extension for new output formats
    - Format-specific optimizations
    
    Subclasses must implement:
    - generate(): Main generation method
    - get_supported_format(): Format identifier
    - validate_config(): Configuration validation
    
    Example:
        >>> generator = ConcreteGenerator(config)
        >>> output = generator.generate(diagram_structure)
    """
    
    def __init__(self, config: Optional[OutputConfig] = None):
        """Initialize the output generator with configuration.
        
        Args:
            config: Output configuration options. If None, uses default config.
        """
        self.config = config or OutputConfig()
        self.validate_config()
    
    @abstractmethod
    def generate(self, structure: DiagramStructure) -> str:
        """Generate output from a diagram structure.
        
        This is the main method that subclasses must implement to convert
        a DiagramStructure into the appropriate output format.
        
        Args:
            structure: Parsed diagram structure containing components,
                      connections, and standalone elements.
        
        Returns:
            Generated output as a string in the target format.
        
        Raises:
            OutputGenerationError: If generation fails due to invalid input
                                  or configuration issues.
        """
        pass
    
    @abstractmethod
    def get_supported_format(self) -> OutputFormat:
        """Get the output format supported by this generator.
        
        Returns:
            OutputFormat enum value indicating the supported format.
        """
        pass
    
    def validate_config(self) -> None:
        """Validate the configuration for this generator.
        
        This method should check that the configuration is valid for
        the specific output format. Base implementation validates common
        options, subclasses can override to add format-specific validation.
        
        Raises:
            ValueError: If configuration is invalid.
        """
        valid_styles = ["standard", "detailed", "concise", "technical"]
        if self.config.format_style not in valid_styles:
            raise ValueError(
                f"Invalid format_style '{self.config.format_style}'. "
                f"Must be one of: {valid_styles}"
            )
        
        if self.config.max_connections_detail < 0:
            raise ValueError(
                "max_connections_detail must be non-negative"
            )
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of the current configuration.
        
        Returns:
            Dictionary containing configuration summary for debugging/logging.
        """
        return {
            "format": self.get_supported_format().value,
            "format_style": self.config.format_style,
            "include_positions": self.config.include_positions,
            "max_connections_detail": self.config.max_connections_detail,
            "custom_options": self.config.custom_options
        }


class OutputGenerationError(Exception):
    """Exception raised when output generation fails.
    
    This exception is raised when an output generator encounters an error
    during the generation process that prevents it from producing valid output.
    
    Attributes:
        message: Human-readable error message
        generator_type: Type of generator that failed
        structure_info: Information about the input structure (optional)
    """
    
    def __init__(self, message: str, generator_type: str = None, 
                 structure_info: Dict[str, Any] = None):
        """Initialize the output generation error.
        
        Args:
            message: Error message describing what went wrong
            generator_type: Name/type of the generator that failed
            structure_info: Optional information about the input structure
        """
        super().__init__(message)
        self.message = message
        self.generator_type = generator_type
        self.structure_info = structure_info or {}
    
    def __str__(self) -> str:
        """Return a formatted error message."""
        parts = [self.message]
        
        if self.generator_type:
            parts.append(f"Generator: {self.generator_type}")
        
        if self.structure_info:
            info_parts = []
            for key, value in self.structure_info.items():
                info_parts.append(f"{key}={value}")
            if info_parts:
                parts.append(f"Structure: {', '.join(info_parts)}")
        
        return " | ".join(parts)


class OutputGeneratorFactory:
    """Factory class for creating output generators.
    
    This factory provides a centralized way to create output generators
    for different formats. It maintains a registry of available generators
    and can create instances based on format requirements.
    
    The factory pattern allows for:
    - Easy registration of new output formats
    - Consistent generator creation
    - Format validation and error handling
    - Plugin-style architecture for extensions
    """
    
    def __init__(self):
        """Initialize the factory with an empty generator registry."""
        self._generators: Dict[OutputFormat, type] = {}
    
    def register_generator(self, format_type: OutputFormat, 
                          generator_class: type) -> None:
        """Register a generator class for a specific output format.
        
        Args:
            format_type: The output format this generator supports
            generator_class: The generator class (must inherit from OutputGenerator)
        
        Raises:
            ValueError: If generator_class is not a valid OutputGenerator subclass
        """
        if not issubclass(generator_class, OutputGenerator):
            raise ValueError(
                f"Generator class {generator_class.__name__} must inherit from OutputGenerator"
            )
        
        self._generators[format_type] = generator_class
    
    def create_generator(self, format_type: OutputFormat, 
                        config: Optional[OutputConfig] = None) -> OutputGenerator:
        """Create a generator instance for the specified format.
        
        Args:
            format_type: The desired output format
            config: Configuration for the generator
        
        Returns:
            Configured generator instance
        
        Raises:
            ValueError: If the format is not supported
        """
        if format_type not in self._generators:
            available_formats = list(self._generators.keys())
            raise ValueError(
                f"Unsupported output format '{format_type.value}'. "
                f"Available formats: {[f.value for f in available_formats]}"
            )
        
        generator_class = self._generators[format_type]
        return generator_class(config)
    
    def get_supported_formats(self) -> list[OutputFormat]:
        """Get a list of all supported output formats.
        
        Returns:
            List of OutputFormat enum values for supported formats
        """
        return list(self._generators.keys())
    
    def is_format_supported(self, format_type: OutputFormat) -> bool:
        """Check if a specific output format is supported.
        
        Args:
            format_type: The format to check
        
        Returns:
            True if the format is supported, False otherwise
        """
        return format_type in self._generators


# Global factory instance for the library
_global_factory = OutputGeneratorFactory()


def get_output_factory() -> OutputGeneratorFactory:
    """Get the global output generator factory instance.
    
    Returns:
        The global OutputGeneratorFactory instance
    """
    return _global_factory


def register_output_generator(format_type: OutputFormat, 
                             generator_class: type) -> None:
    """Register a generator class with the global factory.
    
    This is a convenience function for registering generators with the
    global factory instance.
    
    Args:
        format_type: The output format this generator supports
        generator_class: The generator class
    """
    _global_factory.register_generator(format_type, generator_class)