"""Mermaid diagram generation from Excalidraw structures.

This module provides generators for converting parsed Excalidraw diagrams
into Mermaid diagram syntax. It supports multiple Mermaid diagram types
and provides automatic diagram type detection.

Classes:
    MermaidGenerator: Main generator for Mermaid diagrams
    MermaidFlowchartGenerator: Specialized flowchart generator
    MermaidGraphGenerator: Specialized graph generator
    DiagramTypeDetector: Automatic diagram type detection
    NodeIdManager: Node ID generation and management
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Set, Optional, Tuple, Any
import re
from dataclasses import dataclass

from .models import DiagramStructure, Component, Connection, BaseElement
from .output_generator import (
    OutputGenerator, OutputFormat, OutputConfig, OutputGenerationError
)
from .node_id_manager import NodeIdManager


class MermaidDiagramType(Enum):
    """Types of Mermaid diagrams that can be generated."""
    FLOWCHART = "flowchart"
    GRAPH = "graph"
    MINDMAP = "mindmap"
    # Future diagram types:
    # SEQUENCE = "sequenceDiagram"
    # CLASS = "classDiagram"


class MermaidDirection(Enum):
    """Direction options for Mermaid diagrams."""
    TOP_DOWN = "TD"      # Top to bottom
    BOTTOM_UP = "BU"     # Bottom to top  
    LEFT_RIGHT = "LR"    # Left to right
    RIGHT_LEFT = "RL"    # Right to left


class MermaidTheme(Enum):
    """Available Mermaid themes for styling."""
    DEFAULT = "default"
    NEUTRAL = "neutral"
    DARK = "dark"
    FOREST = "forest"
    BASE = "base"


class MermaidFormatStyle(Enum):
    """Formatting styles for Mermaid output."""
    COMPACT = "compact"      # Minimal whitespace, single lines
    READABLE = "readable"    # Standard formatting with proper indentation
    VERBOSE = "verbose"      # Extra spacing and comments


@dataclass
class MermaidStylingConfig:
    """Configuration for Mermaid diagram styling and theming.
    
    Attributes:
        theme: Theme to apply to the diagram
        custom_node_styles: Custom CSS-like styles for specific node types
        custom_edge_styles: Custom styles for connections/edges
        color_scheme: Custom color scheme override
        font_config: Font configuration options
    """
    theme: MermaidTheme = MermaidTheme.DEFAULT
    custom_node_styles: Dict[str, Dict[str, str]] = None
    custom_edge_styles: Dict[str, str] = None
    color_scheme: Dict[str, str] = None
    font_config: Dict[str, str] = None
    
    def __post_init__(self):
        """Initialize default styling configurations."""
        if self.custom_node_styles is None:
            self.custom_node_styles = {}
        
        if self.custom_edge_styles is None:
            self.custom_edge_styles = {}
        
        if self.color_scheme is None:
            self.color_scheme = {
                "primary": "#0066cc",
                "secondary": "#66cc00", 
                "accent": "#cc6600",
                "background": "#ffffff",
                "text": "#333333"
            }
        
        if self.font_config is None:
            self.font_config = {
                "family": "Arial, sans-serif",
                "size": "14px",
                "weight": "normal"
            }


@dataclass
class MermaidConfig:
    """Comprehensive configuration for Mermaid diagram generation.
    
    This class provides extensive configuration options for customizing
    Mermaid diagram output, including diagram type, layout, formatting,
    styling, and node shape customization.
    
    Attributes:
        diagram_type: Type of Mermaid diagram to generate (auto-detect if None)
        direction: Direction for the diagram layout
        format_style: Formatting style for output (compact, readable, verbose)
        auto_detect_type: Whether to automatically detect diagram type
        include_styling: Whether to include styling information
        styling_config: Detailed styling and theming configuration
        node_shape_mapping: Custom mapping of element types to Mermaid shapes
        connection_style_mapping: Custom mapping for connection styles
        layout_options: Additional layout configuration options
        validation_options: Options for output validation and error handling
    """
    # Core diagram configuration
    diagram_type: Optional[MermaidDiagramType] = None
    direction: MermaidDirection = MermaidDirection.TOP_DOWN
    format_style: MermaidFormatStyle = MermaidFormatStyle.READABLE
    auto_detect_type: bool = True
    
    # Styling and theming
    include_styling: bool = False
    styling_config: MermaidStylingConfig = None
    
    # Node and connection customization
    node_shape_mapping: Dict[str, str] = None
    connection_style_mapping: Dict[str, str] = None
    
    # Layout and formatting options
    layout_options: Dict[str, Any] = None
    
    # Validation and error handling
    validation_options: Dict[str, bool] = None
    
    # Performance optimization options
    performance_options: Dict[str, Any] = None
    
    def __post_init__(self):
        """Initialize default configurations for all options."""
        # Initialize styling config
        if self.styling_config is None:
            self.styling_config = MermaidStylingConfig()
        
        # Initialize default node shape mapping
        if self.node_shape_mapping is None:
            self.node_shape_mapping = {
                "rectangle": "rect",
                "ellipse": "circle", 
                "diamond": "diamond",
                "triangle": "triangle",
                "hexagon": "hexagon",
                "parallelogram": "parallelogram",
                "trapezoid": "trapezoid",
                "cylinder": "cylinder",
                "cloud": "cloud",
                "subroutine": "subroutine"
            }
        
        # Initialize connection style mapping
        if self.connection_style_mapping is None:
            self.connection_style_mapping = {
                "solid": "-->",
                "dashed": "-.->",
                "dotted": "..>",
                "thick": "==>",
                "invisible": "~~~"
            }
        
        # Initialize layout options
        if self.layout_options is None:
            self.layout_options = {
                "node_spacing": "standard",  # compact, standard, wide
                "rank_separation": "auto",   # auto, small, medium, large
                "subgraph_padding": "medium", # small, medium, large
                "edge_length": "auto",       # auto, short, medium, long
                "cluster_nodes": False,      # whether to group related nodes
                "optimize_layout": True      # whether to optimize node positioning
            }
        
        # Initialize validation options
        if self.validation_options is None:
            self.validation_options = {
                "validate_syntax": True,     # validate Mermaid syntax
                "check_node_ids": True,      # check for valid node IDs
                "warn_on_conflicts": True,   # warn about ID conflicts
                "strict_mode": False         # strict validation mode
            }
        
        # Initialize performance options
        if self.performance_options is None:
            self.performance_options = {
                "enable_id_caching": True,        # enable ID caching
                "enable_label_caching": True,     # enable label sanitization caching
                "enable_connection_caching": True, # enable connection processing caching
                "fast_id_generation": False,      # use fast ID generation
                "skip_validation": False,         # skip expensive validation
                "minimal_sanitization": False,    # reduce text sanitization
                "batch_size": 100,                # batch processing size
                "enable_profiling": False,        # enable performance profiling
                "max_cache_size": 10000          # maximum cache size
            }
    
    def get_compact_format(self) -> bool:
        """Check if compact formatting is enabled.
        
        Returns:
            True if compact formatting should be used
        """
        return self.format_style == MermaidFormatStyle.COMPACT
    
    def get_verbose_format(self) -> bool:
        """Check if verbose formatting is enabled.
        
        Returns:
            True if verbose formatting should be used
        """
        return self.format_style == MermaidFormatStyle.VERBOSE
    
    def get_node_shape(self, element_type: str) -> str:
        """Get the Mermaid shape for a given element type.
        
        Args:
            element_type: The type of element (rectangle, ellipse, etc.)
            
        Returns:
            Mermaid shape identifier
        """
        return self.node_shape_mapping.get(element_type.lower(), "rect")
    
    def get_connection_style(self, style_name: str) -> str:
        """Get the Mermaid connection syntax for a given style.
        
        Args:
            style_name: The style name (solid, dashed, etc.)
            
        Returns:
            Mermaid connection syntax
        """
        return self.connection_style_mapping.get(style_name.lower(), "-->")
    
    def should_include_theme(self) -> bool:
        """Check if theme information should be included in output.
        
        Returns:
            True if theme should be included
        """
        return (self.include_styling and 
                self.styling_config.theme != MermaidTheme.DEFAULT)
    
    def get_indentation(self) -> str:
        """Get the appropriate indentation string based on format style.
        
        Returns:
            Indentation string (spaces or empty)
        """
        if self.format_style == MermaidFormatStyle.COMPACT:
            return ""
        elif self.format_style == MermaidFormatStyle.VERBOSE:
            return "    "  # 4 spaces
        else:  # READABLE
            return "    "  # 4 spaces
    
    def get_line_separator(self) -> str:
        """Get the appropriate line separator based on format style.
        
        Returns:
            Line separator string
        """
        if self.format_style == MermaidFormatStyle.VERBOSE:
            return "\n\n"  # Extra spacing
        else:
            return "\n"
    
    def validate_configuration(self) -> None:
        """Validate the configuration for consistency and correctness.
        
        Raises:
            ValueError: If configuration is invalid
        """
        # Validate direction
        if not isinstance(self.direction, MermaidDirection):
            raise ValueError(f"Invalid direction: {self.direction}")
        
        # Validate diagram type if specified
        if (self.diagram_type is not None and 
            not isinstance(self.diagram_type, MermaidDiagramType)):
            raise ValueError(f"Invalid diagram type: {self.diagram_type}")
        
        # Validate format style
        if not isinstance(self.format_style, MermaidFormatStyle):
            raise ValueError(f"Invalid format style: {self.format_style}")
        
        # Validate node shape mapping
        if self.node_shape_mapping:
            for element_type, shape in self.node_shape_mapping.items():
                if not isinstance(element_type, str) or not isinstance(shape, str):
                    raise ValueError(
                        f"Invalid node shape mapping: {element_type} -> {shape}"
                    )
        
        # Validate connection style mapping
        if self.connection_style_mapping:
            for style_name, syntax in self.connection_style_mapping.items():
                if not isinstance(style_name, str) or not isinstance(syntax, str):
                    raise ValueError(
                        f"Invalid connection style mapping: {style_name} -> {syntax}"
                    )
        
        # Validate layout options
        if self.layout_options:
            valid_spacing = ["compact", "standard", "wide"]
            if self.layout_options.get("node_spacing") not in valid_spacing:
                raise ValueError(
                    f"Invalid node_spacing. Must be one of: {valid_spacing}"
                )
            
            valid_separation = ["auto", "small", "medium", "large"]
            if self.layout_options.get("rank_separation") not in valid_separation:
                raise ValueError(
                    f"Invalid rank_separation. Must be one of: {valid_separation}"
                )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for serialization.
        
        Returns:
            Dictionary representation of the configuration
        """
        return {
            "diagram_type": self.diagram_type.value if self.diagram_type else None,
            "direction": self.direction.value,
            "format_style": self.format_style.value,
            "auto_detect_type": self.auto_detect_type,
            "include_styling": self.include_styling,
            "styling_config": {
                "theme": self.styling_config.theme.value,
                "custom_node_styles": self.styling_config.custom_node_styles,
                "custom_edge_styles": self.styling_config.custom_edge_styles,
                "color_scheme": self.styling_config.color_scheme,
                "font_config": self.styling_config.font_config
            },
            "node_shape_mapping": self.node_shape_mapping,
            "connection_style_mapping": self.connection_style_mapping,
            "layout_options": self.layout_options,
            "validation_options": self.validation_options
        }
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'MermaidConfig':
        """Create configuration from dictionary.
        
        Args:
            config_dict: Dictionary containing configuration values
            
        Returns:
            MermaidConfig instance
        """
        # Convert enum values back from strings
        diagram_type = None
        if config_dict.get("diagram_type"):
            diagram_type = MermaidDiagramType(config_dict["diagram_type"])
        
        direction = MermaidDirection(config_dict.get("direction", "TD"))
        format_style = MermaidFormatStyle(config_dict.get("format_style", "readable"))
        
        # Create styling config
        styling_dict = config_dict.get("styling_config", {})
        styling_config = MermaidStylingConfig(
            theme=MermaidTheme(styling_dict.get("theme", "default")),
            custom_node_styles=styling_dict.get("custom_node_styles"),
            custom_edge_styles=styling_dict.get("custom_edge_styles"),
            color_scheme=styling_dict.get("color_scheme"),
            font_config=styling_dict.get("font_config")
        )
        
        return cls(
            diagram_type=diagram_type,
            direction=direction,
            format_style=format_style,
            auto_detect_type=config_dict.get("auto_detect_type", True),
            include_styling=config_dict.get("include_styling", False),
            styling_config=styling_config,
            node_shape_mapping=config_dict.get("node_shape_mapping"),
            connection_style_mapping=config_dict.get("connection_style_mapping"),
            layout_options=config_dict.get("layout_options"),
            validation_options=config_dict.get("validation_options")
        )
    
    def create_preset(self, preset_name: str) -> 'MermaidConfig':
        """Create a configuration preset for common use cases.
        
        Args:
            preset_name: Name of the preset to create
            
        Returns:
            New MermaidConfig instance with preset values
            
        Raises:
            ValueError: If preset name is not recognized
        """
        presets = {
            "minimal": {
                "format_style": MermaidFormatStyle.COMPACT,
                "include_styling": False,
                "auto_detect_type": True,
                "validation_options": {"validate_syntax": False}
            },
            "standard": {
                "format_style": MermaidFormatStyle.READABLE,
                "include_styling": False,
                "auto_detect_type": True
            },
            "styled": {
                "format_style": MermaidFormatStyle.READABLE,
                "include_styling": True,
                "auto_detect_type": True,
                "styling_config": MermaidStylingConfig(theme=MermaidTheme.FOREST)
            },
            "verbose": {
                "format_style": MermaidFormatStyle.VERBOSE,
                "include_styling": True,
                "auto_detect_type": True,
                "validation_options": {"validate_syntax": True, "strict_mode": True}
            }
        }
        
        if preset_name not in presets:
            available_presets = list(presets.keys())
            raise ValueError(
                f"Unknown preset '{preset_name}'. Available presets: {available_presets}"
            )
        
        preset_config = presets[preset_name]
        
        # Create new config with current values as base
        new_config = MermaidConfig(
            diagram_type=self.diagram_type,
            direction=self.direction,
            format_style=preset_config.get("format_style", self.format_style),
            auto_detect_type=preset_config.get("auto_detect_type", self.auto_detect_type),
            include_styling=preset_config.get("include_styling", self.include_styling),
            styling_config=preset_config.get("styling_config", self.styling_config),
            node_shape_mapping=self.node_shape_mapping,
            connection_style_mapping=self.connection_style_mapping,
            layout_options=self.layout_options,
            validation_options=preset_config.get("validation_options", self.validation_options)
        )
        
        return new_config



class DiagramTypeDetector:
    """Detects the most appropriate Mermaid diagram type for a structure.
    
    This class analyzes the diagram structure and relationships to determine
    which Mermaid diagram type would best represent the content.
    """
    
    def detect_diagram_type(self, structure: DiagramStructure) -> MermaidDiagramType:
        """Detect the most appropriate Mermaid diagram type.
        
        Args:
            structure: Parsed diagram structure
            
        Returns:
            Recommended MermaidDiagramType
        """
        if not structure.components:
            return MermaidDiagramType.FLOWCHART  # Default
        
        # Analyze structure characteristics
        total_components = len(structure.components)
        total_connections = len(structure.connections)
        
        # Check for mind map pattern (central node with branches)
        if self._is_mind_map_pattern(structure):
            return MermaidDiagramType.MINDMAP
        
        # Check for flowchart pattern (linear flow with decisions)
        if self._is_flowchart_pattern(structure):
            return MermaidDiagramType.FLOWCHART
        
        # Check for graph pattern (network topology)
        if self._is_graph_pattern(structure):
            return MermaidDiagramType.GRAPH
        
        # Default to flowchart
        return MermaidDiagramType.FLOWCHART
    
    def _is_mind_map_pattern(self, structure: DiagramStructure) -> bool:
        """Check if the structure matches a mind map pattern."""
        if len(structure.components) < 3:
            return False
        
        # Look for a central node with multiple connections
        connection_counts = {}
        for connection in structure.connections:
            source_id = connection.source_component.shape.id
            target_id = connection.target_component.shape.id
            
            connection_counts[source_id] = connection_counts.get(source_id, 0) + 1
            connection_counts[target_id] = connection_counts.get(target_id, 0) + 1
        
        if not connection_counts:
            return False
        
        # Check if there's a node with significantly more connections
        max_connections = max(connection_counts.values())
        highly_connected_nodes = [
            node_id for node_id, count in connection_counts.items() 
            if count >= max_connections * 0.8
        ]
        
        # Mind map typically has 1-2 central nodes
        return len(highly_connected_nodes) <= 2 and max_connections >= 3
    
    def _is_flowchart_pattern(self, structure: DiagramStructure) -> bool:
        """Check if the structure matches a flowchart pattern."""
        if len(structure.components) < 2:
            return False
        
        # Look for linear flow characteristics
        # Check for start/end nodes (nodes with only one connection)
        connection_counts = {}
        for connection in structure.connections:
            source_id = connection.source_component.shape.id
            target_id = connection.target_component.shape.id
            
            connection_counts[source_id] = connection_counts.get(source_id, 0) + 1
            connection_counts[target_id] = connection_counts.get(target_id, 0) + 1
        
        if not connection_counts:
            return True  # No connections, could be flowchart
        
        # Count nodes with 1 connection (start/end nodes)
        terminal_nodes = sum(1 for count in connection_counts.values() if count == 1)
        
        # Flowcharts typically have clear start/end points
        return terminal_nodes >= 2
    
    def _is_graph_pattern(self, structure: DiagramStructure) -> bool:
        """Check if the structure matches a graph/network pattern."""
        if len(structure.components) < 3:
            return False
        
        # Look for network characteristics
        # Check for bidirectional connections or complex topology
        bidirectional_pairs = set()
        connections_by_pair = {}
        
        for connection in structure.connections:
            source_id = connection.source_component.shape.id
            target_id = connection.target_component.shape.id
            
            pair = tuple(sorted([source_id, target_id]))
            if pair not in connections_by_pair:
                connections_by_pair[pair] = []
            connections_by_pair[pair].append(connection)
        
        # Count bidirectional connections
        bidirectional_count = sum(
            1 for connections in connections_by_pair.values() 
            if len(connections) > 1
        )
        
        # Graph pattern if significant bidirectional connections
        total_pairs = len(connections_by_pair)
        if total_pairs > 0:
            bidirectional_ratio = bidirectional_count / total_pairs
            return bidirectional_ratio > 0.3  # 30% or more bidirectional
        
        return False


class MermaidFlowchartGenerator:
    """Specialized generator for Mermaid flowchart diagrams.
    
    This class generates Mermaid flowchart syntax specifically optimized for
    process diagrams. It provides enhanced node shape mapping, connection
    styling, and label handling for flowchart-specific requirements.
    
    Features:
    - Comprehensive node shape mapping (rectangle → rect, ellipse → circle, etc.)
    - Connection syntax with labels and styling options
    - Special character handling for text and arrow labels
    - Flowchart-specific formatting and layout options
    
    Example:
        >>> config = MermaidConfig(direction=MermaidDirection.TOP_DOWN)
        >>> generator = MermaidFlowchartGenerator(config)
        >>> flowchart = generator.generate_flowchart(diagram_structure)
    """
    
    def __init__(self, config: Optional[MermaidConfig] = None):
        """Initialize the flowchart generator.
        
        Args:
            config: Mermaid configuration options. If None, uses default config.
        """
        self.config = config or MermaidConfig()
        self.node_id_manager = NodeIdManager()
    
    def generate_flowchart(self, structure: DiagramStructure) -> str:
        """Generate Mermaid flowchart syntax from a diagram structure.
        
        Args:
            structure: Parsed diagram structure containing components and connections
            
        Returns:
            Mermaid flowchart syntax as a string
            
        Raises:
            OutputGenerationError: If generation fails
        """
        try:
            lines = []
            indent = self.config.get_indentation()
            line_sep = self.config.get_line_separator()
            
            # Header with direction
            direction = self.config.direction.value
            lines.append(f"flowchart {direction}")
            
            # Add theme if enabled
            if self.config.should_include_theme():
                theme_line = f"%%{{init: {{'theme':'{self.config.styling_config.theme.value}'}}}}%%"
                lines.append(theme_line)
            
            # Add verbose comment if enabled
            if self.config.get_verbose_format():
                lines.append("")
                lines.append(f"{indent}%% Generated from Excalidraw diagram")
                lines.append(f"{indent}%% Components: {len(structure.components)}")
                lines.append(f"{indent}%% Connections: {len(structure.connections)}")
                lines.append("")
            
            # Add nodes with proper shape mapping
            if structure.components:
                if self.config.get_verbose_format():
                    lines.append(f"{indent}%% Node definitions")
                
                for component in structure.components:
                    node_line = self._generate_node_definition(component)
                    if node_line:
                        lines.append(f"{indent}{node_line}")
                
                if self.config.get_verbose_format():
                    lines.append("")
            
            # Add connections with labels and styling
            if structure.connections:
                if self.config.get_verbose_format():
                    lines.append(f"{indent}%% Connection definitions")
                
                for connection in structure.connections:
                    connection_line = self._generate_connection_definition(connection)
                    if connection_line:
                        lines.append(f"{indent}{connection_line}")
                
                if self.config.get_verbose_format():
                    lines.append("")
            
            # Add standalone elements if any
            if structure.standalone_elements:
                if self.config.get_verbose_format():
                    lines.append(f"{indent}%% Standalone elements")
                
                for element in structure.standalone_elements:
                    standalone_line = self._generate_standalone_element(element)
                    if standalone_line:
                        lines.append(f"{indent}{standalone_line}")
                
                if self.config.get_verbose_format():
                    lines.append("")
            
            # Add styling if enabled
            if self.config.include_styling:
                styling_lines = self._generate_styling()
                if styling_lines:
                    if self.config.get_verbose_format():
                        lines.append(f"{indent}%% Custom styling")
                    lines.extend([f"{indent}{line}" for line in styling_lines])
            
            return line_sep.join(lines) if self.config.get_verbose_format() else "\n".join(lines)
            
        except Exception as e:
            structure_info = {}
            if structure is not None:
                structure_info = {
                    "components": len(structure.components),
                    "connections": len(structure.connections),
                    "standalone_elements": len(structure.standalone_elements)
                }
            else:
                structure_info = {"error": "structure is None"}
            
            raise OutputGenerationError(
                f"Failed to generate Mermaid flowchart: {str(e)}",
                generator_type="MermaidFlowchartGenerator",
                structure_info=structure_info
            )
    
    def _generate_node_definition(self, component: Component) -> str:
        """Generate a node definition line for a component.
        
        Args:
            component: The component to generate a node for
            
        Returns:
            Mermaid node definition string
        """
        # Get node ID
        node_id = self.node_id_manager.get_node_id(
            component.shape.id,
            component.label.text if component.label else ""
        )
        
        # Get sanitized label
        label = self._get_component_label(component)
        
        # Get appropriate shape syntax
        shape_syntax = self._get_flowchart_shape(component.shape, label)
        
        return f"{node_id}{shape_syntax}"
    
    def _generate_connection_definition(self, connection: Connection) -> str:
        """Generate a connection definition line.
        
        Args:
            connection: The connection to generate syntax for
            
        Returns:
            Mermaid connection definition string
        """
        # Get source and target node IDs
        source_id = self.node_id_manager.get_node_id(
            connection.source_component.shape.id,
            connection.source_component.label.text if connection.source_component.label else ""
        )
        target_id = self.node_id_manager.get_node_id(
            connection.target_component.shape.id,
            connection.target_component.label.text if connection.target_component.label else ""
        )
        
        # Generate connection with optional label
        connection_syntax = self._get_connection_syntax(connection)
        
        return f"{source_id} {connection_syntax} {target_id}"
    
    def _generate_standalone_element(self, element: BaseElement) -> str:
        """Generate a definition for a standalone element.
        
        Args:
            element: The standalone element
            
        Returns:
            Mermaid node definition string
        """
        # Get node ID
        node_id = self.node_id_manager.get_node_id(element.id, "")
        
        # Get label from element if it's a text element
        label = ""
        if hasattr(element, 'text') and element.text:
            label = self.node_id_manager.sanitize_label(element.text.strip())
        else:
            label = "Standalone"
        
        # Get appropriate shape syntax
        shape_syntax = self._get_flowchart_shape(element, label)
        
        return f"{node_id}{shape_syntax}"
    
    def _get_component_label(self, component: Component) -> str:
        """Get sanitized label for a component.
        
        Args:
            component: The component to get label for
            
        Returns:
            Sanitized label string
        """
        if component.label and component.label.text.strip():
            return self.node_id_manager.sanitize_label(component.label.text.strip())
        else:
            return "Unlabeled"
    
    def _get_flowchart_shape(self, element: BaseElement, label: str) -> str:
        """Get the appropriate Mermaid flowchart shape syntax for an element.
        
        This method implements comprehensive shape mapping optimized for flowcharts
        using the enhanced configuration system for maximum customization.
        
        Args:
            element: The diagram element
            label: The sanitized label text
            
        Returns:
            Mermaid shape syntax string
        """
        element_type = element.type.lower()
        
        # Use configuration's shape mapping
        shape_type = self.config.get_node_shape(element_type)
        
        # Generate appropriate Mermaid syntax based on shape type
        shape_syntax_map = {
            "rect": f"[\"{label}\"]",
            "circle": f"((\"{label}\"))",
            "diamond": f"{{\"{label}\"}}",
            "triangle": f"[\"{label}\"]",  # Mermaid doesn't have native triangle
            "hexagon": f"{{\"{label}\"}}",  # Use diamond syntax for hexagon
            "parallelogram": f"[/\"{label}\"/]",
            "trapezoid": f"[\\\"{label}\"\\]",
            "cylinder": f"[(\"{label}\")]",
            "cloud": f"((\"{label}\"))",  # Use circle for cloud
            "subroutine": f"[[\"{label}\"]]"
        }
        
        return shape_syntax_map.get(shape_type, f"[\"{label}\"]")  # Default to rectangle
    
    def _get_connection_syntax(self, connection: Connection) -> str:
        """Get the appropriate connection syntax with optional labels and styling.
        
        Args:
            connection: The connection to generate syntax for
            
        Returns:
            Mermaid connection syntax string
        """
        # Check if arrow has a label
        arrow_label = ""
        if hasattr(connection.arrow, 'text') and connection.arrow.text:
            arrow_label = self.node_id_manager.sanitize_label(connection.arrow.text.strip())
        
        # Get connection style from configuration
        connection_style = self.config.get_connection_style("solid")  # Default style
        
        # Add label if present
        if arrow_label:
            return f"{connection_style}|\"{arrow_label}\"|"
        else:
            return connection_style
    
    def _generate_styling(self) -> List[str]:
        """Generate styling definitions for the flowchart.
        
        Returns:
            List of styling definition lines
        """
        styling_lines = []
        
        if not self.config.include_styling:
            return styling_lines
        
        # Add custom node styles
        for node_type, styles in self.config.styling_config.custom_node_styles.items():
            style_parts = []
            for property_name, value in styles.items():
                style_parts.append(f"{property_name}:{value}")
            
            if style_parts:
                style_definition = ",".join(style_parts)
                styling_lines.append(f"classDef {node_type} {style_definition}")
        
        # Add color scheme styling
        if self.config.styling_config.color_scheme:
            colors = self.config.styling_config.color_scheme
            if "primary" in colors:
                styling_lines.append(f"classDef primary fill:{colors['primary']}")
            if "secondary" in colors:
                styling_lines.append(f"classDef secondary fill:{colors['secondary']}")
            if "accent" in colors:
                styling_lines.append(f"classDef accent fill:{colors['accent']}")
        
        return styling_lines
    
    def _get_arrow_label(self, arrow: BaseElement) -> str:
        """Extract label from an arrow element.
        
        Args:
            arrow: The arrow element
            
        Returns:
            Arrow label text or empty string
        """
        # Check if arrow has text property
        if hasattr(arrow, 'text') and arrow.text:
            import re
            return re.sub(r'\s+', ' ', arrow.text.strip())
        
        # Check for other label properties that might exist
        if hasattr(arrow, 'label') and arrow.label:
            import re
            return re.sub(r'\s+', ' ', arrow.label.strip())
        
        return ""
    
    def _generate_styling(self) -> List[str]:
        """Generate basic styling definitions for the flowchart.
        
        Returns:
            List of styling definition lines
        """
        styling_lines = []
        
        # Add basic class definitions for different node types
        styling_lines.extend([
            "",  # Empty line for separation
            "    %% Styling",
            "    classDef default fill:#f9f9f9,stroke:#333,stroke-width:2px",
            "    classDef decision fill:#ffe6cc,stroke:#d79b00,stroke-width:2px",
            "    classDef process fill:#e6f3ff,stroke:#0066cc,stroke-width:2px",
            "    classDef terminal fill:#e6ffe6,stroke:#00cc00,stroke-width:2px"
        ])
        
        return styling_lines


class MermaidGraphGenerator:
    """Specialized generator for Mermaid graph diagrams.
    
    This class generates Mermaid graph syntax specifically optimized for
    network and system diagrams. It provides enhanced bidirectional connection
    handling, graph direction detection, and node grouping for complex topologies.
    
    Features:
    - Automatic graph direction detection based on layout
    - Bidirectional connection handling with appropriate syntax
    - Node grouping/subgraphs for complex topologies
    - Network topology optimization for relationship accuracy
    - Support for complex system architecture diagrams
    
    Example:
        >>> config = MermaidConfig(direction=MermaidDirection.LEFT_RIGHT)
        >>> generator = MermaidGraphGenerator(config)
        >>> graph = generator.generate_graph(diagram_structure)
    """
    
    def __init__(self, config: Optional[MermaidConfig] = None):
        """Initialize the graph generator.
        
        Args:
            config: Mermaid configuration options. If None, uses default config.
        """
        self.config = config or MermaidConfig()
        self.node_id_manager = NodeIdManager()
        self._connection_pairs: Dict[Tuple[str, str], List[Connection]] = {}
        self._node_groups: Dict[str, List[Component]] = {}
    
    def generate_graph(self, structure: DiagramStructure) -> str:
        """Generate Mermaid graph syntax from a diagram structure.
        
        Args:
            structure: Parsed diagram structure containing components and connections
            
        Returns:
            Mermaid graph syntax as a string
            
        Raises:
            OutputGenerationError: If generation fails
        """
        try:
            lines = []
            indent = self.config.get_indentation()
            line_sep = self.config.get_line_separator()
            
            # Detect optimal direction if not explicitly set
            direction = self._detect_graph_direction(structure)
            
            # Header with direction
            lines.append(f"graph {direction}")
            
            # Add theme if enabled
            if self.config.should_include_theme():
                theme_line = f"%%{{init: {{'theme':'{self.config.styling_config.theme.value}'}}}}%%"
                lines.append(theme_line)
            
            # Add verbose comment if enabled
            if self.config.get_verbose_format():
                lines.append("")
                lines.append(f"{indent}%% Generated graph from Excalidraw diagram")
                lines.append(f"{indent}%% Components: {len(structure.components)}")
                lines.append(f"{indent}%% Connections: {len(structure.connections)}")
                lines.append("")
            
            # Analyze connections for bidirectional handling
            self._analyze_connections(structure)
            
            # Detect node groups for subgraph generation
            if self.config.layout_options.get("cluster_nodes", False):
                self._detect_node_groups(structure)
            
            # Generate subgraphs if groups are detected
            if self.config.layout_options.get("cluster_nodes", False):
                subgraph_lines = self._generate_subgraphs()
                if subgraph_lines:
                    if self.config.get_verbose_format():
                        lines.append(f"{indent}%% Subgraph definitions")
                    lines.extend([f"{indent}{line}" for line in subgraph_lines])
                    if self.config.get_verbose_format():
                        lines.append("")
            
            # Generate connections with bidirectional handling
            if structure.connections:
                if self.config.get_verbose_format():
                    lines.append(f"{indent}%% Connection definitions")
                
                connection_lines = self._generate_graph_connections()
                lines.extend([f"{indent}{line}" for line in connection_lines])
                
                if self.config.get_verbose_format():
                    lines.append("")
            
            # Add node definitions with labels
            if structure.components:
                if self.config.get_verbose_format():
                    lines.append(f"{indent}%% Node definitions")
                
                node_lines = self._generate_node_definitions(structure)
                lines.extend([f"{indent}{line}" for line in node_lines])
                
                if self.config.get_verbose_format():
                    lines.append("")
            
            # Add standalone elements
            if structure.standalone_elements:
                if self.config.get_verbose_format():
                    lines.append(f"{indent}%% Standalone elements")
                
                for element in structure.standalone_elements:
                    standalone_line = self._generate_standalone_element(element)
                    if standalone_line:
                        lines.append(f"{indent}{standalone_line}")
                
                if self.config.get_verbose_format():
                    lines.append("")
            
            # Add styling if enabled
            if self.config.include_styling:
                styling_lines = self._generate_graph_styling()
                if styling_lines:
                    if self.config.get_verbose_format():
                        lines.append(f"{indent}%% Custom styling")
                    lines.extend([f"{indent}{line}" for line in styling_lines])
            
            return line_sep.join(lines) if self.config.get_verbose_format() else "\n".join(lines)
            
        except Exception as e:
            structure_info = {}
            if structure is not None:
                structure_info = {
                    "components": len(structure.components),
                    "connections": len(structure.connections),
                    "standalone_elements": len(structure.standalone_elements)
                }
            else:
                structure_info = {"error": "structure is None"}
            
            raise OutputGenerationError(
                f"Failed to generate Mermaid graph: {str(e)}",
                generator_type="MermaidGraphGenerator",
                structure_info=structure_info
            )
    
    def _detect_graph_direction(self, structure: DiagramStructure) -> str:
        """Detect optimal graph direction based on component layout.
        
        Analyzes the spatial distribution of components to determine
        whether the graph flows more naturally top-down, left-right, etc.
        
        Args:
            structure: Diagram structure to analyze
            
        Returns:
            Mermaid direction string (TD, LR, etc.)
        """
        if not structure.components:
            return self.config.direction.value
        
        # Calculate bounding box and component distribution
        x_positions = [comp.shape.x for comp in structure.components]
        y_positions = [comp.shape.y for comp in structure.components]
        
        if not x_positions or not y_positions:
            return self.config.direction.value
        
        x_range = max(x_positions) - min(x_positions)
        y_range = max(y_positions) - min(y_positions)
        
        # Determine primary flow direction based on layout
        if x_range > y_range * 1.5:
            # Wider than tall - likely left-right flow
            return MermaidDirection.LEFT_RIGHT.value
        elif y_range > x_range * 1.5:
            # Taller than wide - likely top-down flow
            return MermaidDirection.TOP_DOWN.value
        else:
            # Roughly square - use configured direction
            return self.config.direction.value
    
    def _analyze_connections(self, structure: DiagramStructure) -> None:
        """Analyze connections to identify bidirectional pairs and complex topologies.
        
        Groups connections by node pairs to detect bidirectional relationships
        and prepare for optimized graph generation.
        
        Args:
            structure: Diagram structure containing connections
        """
        self._connection_pairs.clear()
        
        for connection in structure.connections:
            source_id = connection.source_component.shape.id
            target_id = connection.target_component.shape.id
            
            # Create normalized pair key (sorted to handle bidirectional)
            pair_key = tuple(sorted([source_id, target_id]))
            
            if pair_key not in self._connection_pairs:
                self._connection_pairs[pair_key] = []
            
            self._connection_pairs[pair_key].append(connection)
    
    def _detect_node_groups(self, structure: DiagramStructure) -> None:
        """Detect node groups for subgraph generation.
        
        Analyzes component positions and connections to identify
        clusters that should be grouped into subgraphs.
        
        Args:
            structure: Diagram structure to analyze
        """
        self._node_groups.clear()
        
        # Simple clustering based on spatial proximity
        # This is a basic implementation - could be enhanced with more sophisticated clustering
        
        if len(structure.components) < 4:
            # Too few components for meaningful grouping
            return
        
        # Group components by spatial proximity
        grouped_components = set()
        group_id = 0
        
        for component in structure.components:
            if component.shape.id in grouped_components:
                continue
            
            # Find nearby components
            nearby_components = [component]
            grouped_components.add(component.shape.id)
            
            for other_component in structure.components:
                if other_component.shape.id in grouped_components:
                    continue
                
                # Calculate distance
                dx = abs(component.shape.x - other_component.shape.x)
                dy = abs(component.shape.y - other_component.shape.y)
                distance = (dx ** 2 + dy ** 2) ** 0.5
                
                # If components are close and connected, group them
                if distance < 200:  # Threshold for proximity
                    # Check if they're connected
                    connected = any(
                        (conn.source_component.shape.id == component.shape.id and 
                         conn.target_component.shape.id == other_component.shape.id) or
                        (conn.source_component.shape.id == other_component.shape.id and 
                         conn.target_component.shape.id == component.shape.id)
                        for conn in structure.connections
                    )
                    
                    if connected:
                        nearby_components.append(other_component)
                        grouped_components.add(other_component.shape.id)
            
            # Only create groups with multiple components
            if len(nearby_components) > 1:
                group_name = f"group_{group_id}"
                self._node_groups[group_name] = nearby_components
                group_id += 1
    
    def _generate_subgraphs(self) -> List[str]:
        """Generate subgraph definitions for node groups.
        
        Returns:
            List of subgraph definition lines
        """
        lines = []
        
        for group_name, components in self._node_groups.items():
            if len(components) < 2:
                continue
            
            lines.append(f"    subgraph {group_name} [\"{group_name.replace('_', ' ').title()}\"]")
            
            # Add components to subgraph
            for component in components:
                node_id = self.node_id_manager.get_node_id(
                    component.shape.id,
                    component.label.text if component.label else ""
                )
                lines.append(f"        {node_id}")
            
            lines.append("    end")
            lines.append("")  # Empty line for readability
        
        return lines
    
    def _generate_graph_connections(self) -> List[str]:
        """Generate connection definitions with bidirectional handling.
        
        Returns:
            List of connection definition lines
        """
        lines = []
        processed_pairs = set()
        
        for pair_key, connections in self._connection_pairs.items():
            if pair_key in processed_pairs:
                continue
            
            # Get node IDs
            node_ids = list(pair_key)
            source_id = node_ids[0]
            target_id = node_ids[1]
            
            # Get actual node IDs from manager
            source_mermaid_id = None
            target_mermaid_id = None
            
            # Find the components for these IDs
            for connection in connections:
                if source_mermaid_id is None:
                    source_mermaid_id = self.node_id_manager.get_node_id(
                        connection.source_component.shape.id,
                        connection.source_component.label.text if connection.source_component.label else ""
                    )
                if target_mermaid_id is None:
                    target_mermaid_id = self.node_id_manager.get_node_id(
                        connection.target_component.shape.id,
                        connection.target_component.label.text if connection.target_component.label else ""
                    )
            
            if source_mermaid_id is None or target_mermaid_id is None:
                continue
            
            # Determine connection type
            if len(connections) > 1:
                # Multiple connections between same nodes - likely bidirectional
                connection_syntax = self._get_bidirectional_syntax(connections)
                lines.append(f"    {source_mermaid_id} {connection_syntax} {target_mermaid_id}")
            else:
                # Single connection
                connection = connections[0]
                connection_syntax = self._get_unidirectional_syntax(connection)
                
                # Determine actual direction
                actual_source_id = self.node_id_manager.get_node_id(
                    connection.source_component.shape.id,
                    connection.source_component.label.text if connection.source_component.label else ""
                )
                actual_target_id = self.node_id_manager.get_node_id(
                    connection.target_component.shape.id,
                    connection.target_component.label.text if connection.target_component.label else ""
                )
                
                lines.append(f"    {actual_source_id} {connection_syntax} {actual_target_id}")
            
            processed_pairs.add(pair_key)
        
        return lines
    
    def _get_bidirectional_syntax(self, connections: List[Connection]) -> str:
        """Get bidirectional connection syntax.
        
        Args:
            connections: List of connections between the same pair of nodes
            
        Returns:
            Mermaid bidirectional connection syntax
        """
        # Check if any connection has a label
        labels = []
        for connection in connections:
            label = self._get_connection_label(connection)
            if label:
                labels.append(label)
        
        if labels:
            # Use the first label found
            sanitized_label = self.node_id_manager.sanitize_label(labels[0])
            return f"<-->|\"{sanitized_label}\"|"
        else:
            return "<-->"
    
    def _get_unidirectional_syntax(self, connection: Connection) -> str:
        """Get unidirectional connection syntax.
        
        Args:
            connection: Single connection
            
        Returns:
            Mermaid unidirectional connection syntax
        """
        label = self._get_connection_label(connection)
        
        if label:
            sanitized_label = self.node_id_manager.sanitize_label(label)
            return f"-->|\"{sanitized_label}\"|"
        else:
            return "-->"
    
    def _get_connection_label(self, connection: Connection) -> str:
        """Extract label from a connection.
        
        Args:
            connection: Connection to extract label from
            
        Returns:
            Connection label or empty string
        """
        # Check arrow element for text
        if hasattr(connection.arrow, 'text') and connection.arrow.text:
            import re
            return re.sub(r'\s+', ' ', connection.arrow.text.strip())
        
        # Check for other label properties
        if hasattr(connection.arrow, 'label') and connection.arrow.label:
            import re
            return re.sub(r'\s+', ' ', connection.arrow.label.strip())
        
        return ""
    
    def _generate_node_definitions(self, structure: DiagramStructure) -> List[str]:
        """Generate node definitions with labels.
        
        Args:
            structure: Diagram structure
            
        Returns:
            List of node definition lines
        """
        lines = []
        
        for component in structure.components:
            node_id = self.node_id_manager.get_node_id(
                component.shape.id,
                component.label.text if component.label else ""
            )
            
            # Get sanitized label
            if component.label and component.label.text.strip():
                label = self.node_id_manager.sanitize_label(component.label.text.strip())
                # Use simple rectangular nodes for graphs
                lines.append(f"    {node_id}[\"{label}\"]")
        
        return lines
    
    def _generate_standalone_element(self, element: BaseElement) -> str:
        """Generate definition for a standalone element.
        
        Args:
            element: Standalone element
            
        Returns:
            Mermaid node definition string
        """
        node_id = self.node_id_manager.get_node_id(element.id, "")
        
        # Get label from element if it's a text element
        label = ""
        if hasattr(element, 'text') and element.text:
            label = self.node_id_manager.sanitize_label(element.text.strip())
        else:
            label = "Standalone"
        
        return f"{node_id}[\"{label}\"]"
    
    def _generate_graph_styling(self) -> List[str]:
        """Generate styling definitions for graph diagrams.
        
        Returns:
            List of styling definition lines
        """
        styling_lines = []
        
        # Add graph-specific styling
        styling_lines.extend([
            "",  # Empty line for separation
            "    %% Graph Styling",
            "    classDef default fill:#f9f9f9,stroke:#333,stroke-width:2px",
            "    classDef cluster fill:#e6f3ff,stroke:#0066cc,stroke-width:2px,stroke-dasharray: 5 5",
            "    classDef network fill:#fff2e6,stroke:#cc6600,stroke-width:2px",
            "    classDef system fill:#f0f8e6,stroke:#66cc00,stroke-width:2px"
        ])
        
        # Add group-specific styling
        for group_name in self._node_groups.keys():
            styling_lines.append(f"    class {group_name} cluster")
        
        return styling_lines


class MermaidGenerator(OutputGenerator):
    """Main generator for Mermaid diagrams.
    
    This generator converts Excalidraw diagram structures into Mermaid syntax.
    It supports automatic diagram type detection and multiple Mermaid formats.
    """
    
    def __init__(self, config: Optional[OutputConfig] = None, mermaid_config: Optional[MermaidConfig] = None):
        """Initialize the Mermaid generator.
        
        Args:
            config: Output configuration with Mermaid-specific options
            mermaid_config: Direct MermaidConfig instance (takes precedence over config)
        """
        super().__init__(config)
        
        # Use direct MermaidConfig if provided, otherwise extract from OutputConfig
        if mermaid_config is not None:
            self.mermaid_config = mermaid_config
        else:
            # Extract Mermaid-specific configuration from OutputConfig
            mermaid_options = self.config.custom_options.get('mermaid', {})
            
            # Convert string diagram types to enums
            if 'diagram_type' in mermaid_options and isinstance(mermaid_options['diagram_type'], str):
                diagram_type_str = mermaid_options['diagram_type']
                try:
                    mermaid_options['diagram_type'] = MermaidDiagramType(diagram_type_str)
                except ValueError:
                    # Keep as string for now, will be validated later
                    pass
            
            # Convert string directions to enums
            if 'direction' in mermaid_options and isinstance(mermaid_options['direction'], str):
                direction_str = mermaid_options['direction']
                try:
                    mermaid_options['direction'] = MermaidDirection(direction_str)
                except ValueError:
                    # Keep as string for now, will be validated later
                    pass
            
            # Convert string format styles to enums
            if 'format_style' in mermaid_options and isinstance(mermaid_options['format_style'], str):
                format_style_str = mermaid_options['format_style']
                try:
                    mermaid_options['format_style'] = MermaidFormatStyle(format_style_str)
                except ValueError:
                    # Keep as string for now, will be validated later
                    pass
            
            self.mermaid_config = MermaidConfig(**mermaid_options)
        
        # Validate the configuration
        self.mermaid_config.validate_configuration()
        
        # Initialize components
        self.node_id_manager = NodeIdManager()
        self.diagram_type_detector = DiagramTypeDetector()
    
    def get_supported_format(self) -> OutputFormat:
        """Get the output format supported by this generator.
        
        Returns:
            OutputFormat.MERMAID for Mermaid diagram syntax
        """
        return OutputFormat.MERMAID
    
    def generate(self, structure: DiagramStructure) -> str:
        """Generate Mermaid diagram syntax from a diagram structure.
        
        Args:
            structure: Parsed diagram structure
            
        Returns:
            Mermaid diagram syntax as a string
            
        Raises:
            OutputGenerationError: If generation fails
        """
        try:
            # Detect or use configured diagram type
            diagram_type = self.mermaid_config.diagram_type
            if diagram_type is None and self.mermaid_config.auto_detect_type:
                diagram_type = self.diagram_type_detector.detect_diagram_type(structure)
            elif diagram_type is None:
                diagram_type = MermaidDiagramType.FLOWCHART  # Default
            
            # Generate based on diagram type
            if diagram_type == MermaidDiagramType.FLOWCHART:
                return self._generate_flowchart(structure)
            elif diagram_type == MermaidDiagramType.GRAPH:
                return self._generate_graph(structure)
            elif diagram_type == MermaidDiagramType.MINDMAP:
                return self._generate_mindmap(structure)
            else:
                raise OutputGenerationError(
                    f"Unsupported diagram type: {diagram_type}",
                    generator_type="MermaidGenerator"
                )
        
        except Exception as e:
            if isinstance(e, OutputGenerationError):
                raise
            
            structure_info = {
                "components": len(structure.components),
                "connections": len(structure.connections),
                "standalone_elements": len(structure.standalone_elements)
            }
            
            raise OutputGenerationError(
                f"Failed to generate Mermaid diagram: {str(e)}",
                generator_type="MermaidGenerator",
                structure_info=structure_info
            )
    
    def _generate_flowchart(self, structure: DiagramStructure) -> str:
        """Generate Mermaid flowchart syntax using the specialized flowchart generator.
        
        Args:
            structure: Diagram structure
            
        Returns:
            Mermaid flowchart syntax
        """
        # Use the specialized flowchart generator
        flowchart_generator = MermaidFlowchartGenerator(self.mermaid_config)
        return flowchart_generator.generate_flowchart(structure)
    
    def _generate_graph(self, structure: DiagramStructure) -> str:
        """Generate Mermaid graph syntax using the specialized graph generator.
        
        Args:
            structure: Diagram structure
            
        Returns:
            Mermaid graph syntax
        """
        # Use the specialized graph generator
        graph_generator = MermaidGraphGenerator(self.mermaid_config)
        return graph_generator.generate_graph(structure)
    
    def _generate_mindmap(self, structure: DiagramStructure) -> str:
        """Generate Mermaid mindmap syntax.
        
        Args:
            structure: Diagram structure
            
        Returns:
            Mermaid mindmap syntax
        """
        # Note: Mermaid mindmap syntax is quite different
        # For now, fall back to flowchart format
        # TODO: Implement proper mindmap syntax in future version
        return self._generate_flowchart(structure)
    
    def _get_mermaid_shape(self, element: BaseElement, label: str) -> str:
        """Get the appropriate Mermaid shape syntax for an element.
        
        Args:
            element: The diagram element
            label: The sanitized label text
            
        Returns:
            Mermaid shape syntax string
        """
        element_type = element.type.lower()
        
        # Map element types to Mermaid shapes
        if element_type == "rectangle":
            return f"[\"{label}\"]"
        elif element_type == "ellipse":
            return f"((\"{label}\"))"
        elif element_type == "diamond":
            return f"{{\"{label}\"}}"
        elif element_type == "triangle":
            return f"[\"{label}\"]"
        else:
            # Default to rectangle
            return f"[\"{label}\"]"
    
    def validate_config(self) -> None:
        """Validate Mermaid-specific configuration.
        
        Raises:
            ValueError: If configuration is invalid
        """
        super().validate_config()
        
        # Validate Mermaid-specific options
        if 'mermaid' in self.config.custom_options:
            mermaid_opts = self.config.custom_options['mermaid']
            
            if 'diagram_type' in mermaid_opts:
                diagram_type = mermaid_opts['diagram_type']
                if diagram_type and not isinstance(diagram_type, MermaidDiagramType):
                    if isinstance(diagram_type, str):
                        try:
                            MermaidDiagramType(diagram_type)
                        except ValueError:
                            valid_types = [t.value for t in MermaidDiagramType]
                            raise ValueError(
                                f"Invalid diagram_type '{diagram_type}'. "
                                f"Must be one of: {valid_types}"
                            )
            
            if 'direction' in mermaid_opts:
                direction = mermaid_opts['direction']
                if direction and not isinstance(direction, MermaidDirection):
                    if isinstance(direction, str):
                        try:
                            MermaidDirection(direction)
                        except ValueError:
                            valid_directions = [d.value for d in MermaidDirection]
                            raise ValueError(
                                f"Invalid direction '{direction}'. "
                                f"Must be one of: {valid_directions}"
                            )