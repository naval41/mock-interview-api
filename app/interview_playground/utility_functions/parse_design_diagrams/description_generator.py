"""
Description generation for Excalidraw diagrams.
"""

from typing import List, Optional, Dict, Any
from .models import (
    BaseElement, TextElement, ArrowElement, RectangleElement,
    Component, Connection, DiagramStructure
)
from .output_generator import OutputGenerator, OutputFormat


class DescriptionGenerator(OutputGenerator):
    """
    Generates natural language descriptions of Excalidraw diagrams.
    
    This class converts structured diagram data into human-readable text descriptions
    that capture the essential elements and relationships in the diagram. It uses
    natural language templates and formatting rules to create coherent descriptions.
    
    The generator handles different types of diagram elements:
        - Components: Labeled shapes (rectangles, circles, etc.)
        - Connections: Directional relationships via arrows
        - Standalone elements: Unconnected text, shapes, or other elements
    
    Description features:
        - Natural language flow with proper grammar
        - Directional language for connections (flows, connects, etc.)
        - Handling of multiple elements with appropriate conjunctions
        - Graceful handling of unlabeled or empty elements
        - Configurable output formats and verbosity levels
    
    Example:
        >>> generator = DescriptionGenerator()
        >>> description = generator.generate_description(diagram_structure)
        >>> print(description)
        'The diagram contains a rectangle labeled "Start" and a rectangle labeled "End". 
         "Start" connects to "End".'
    """
    
    def __init__(self, config=None, format_style=None, include_positions=None, max_connections_detail=None):
        """
        Initialize the description generator with configuration options.
        
        Args:
            config: OutputConfig instance with all settings
            format_style: Output format style (deprecated, use config)
            include_positions: Include position info (deprecated, use config)
            max_connections_detail: Max connections detail (deprecated, use config)
        """
        # Handle backward compatibility with old parameter style
        if config is None:
            from .output_generator import OutputConfig
            config = OutputConfig(
                format_style=format_style or "standard",
                include_positions=include_positions or False,
                max_connections_detail=max_connections_detail or 10
            )
        
        # Initialize parent class
        super().__init__(config)
        
        # Set convenience properties for backward compatibility
        self.format_style = self.config.format_style
        self.include_positions = self.config.include_positions
        self.max_connections_detail = self.config.max_connections_detail
        
        # Enhanced natural language templates
        self._connection_templates = {
            "left-to-right": [
                "{source} connects to {target}",
                "{source} flows to {target}",
                "{source} points to {target}",
                "{source} leads to {target}"
            ],
            "right-to-left": [
                "{source} connects to {target}",
                "{source} returns to {target}",
                "{source} flows back to {target}"
            ],
            "top-to-bottom": [
                "{source} flows down to {target}",
                "{source} cascades to {target}",
                "{source} leads down to {target}"
            ],
            "bottom-to-top": [
                "{source} flows up to {target}",
                "{source} feeds back to {target}",
                "{source} reports to {target}"
            ],
            "bidirectional": [
                "{source} and {target} are connected bidirectionally",
                "{source} and {target} have a two-way connection"
            ]
        }
        
        self._shape_descriptions = {
            "rectangle": ["rectangle", "box", "container"],
            "ellipse": ["circle", "oval", "ellipse"],
            "diamond": ["diamond", "decision point", "rhombus"],
            "triangle": ["triangle", "arrow shape"],
            "hexagon": ["hexagon", "process shape"]
        }

    def generate_description(self, structure: DiagramStructure) -> str:
        """
        Converts structured diagram data to natural language description.
        
        This is the main entry point for description generation. It processes each
        type of diagram element (components, connections, standalone elements) and
        combines them into a coherent natural language description.
        
        Args:
            structure (DiagramStructure): Structured diagram data containing:
                - components: List of Component objects (shapes with labels)
                - connections: List of Connection objects (arrows between components)
                - standalone_elements: List of unconnected BaseElement objects
        
        Returns:
            str: Natural language description of the diagram. Returns a message
                indicating an empty diagram if no recognizable elements are found.
        
        Example:
            >>> structure = DiagramStructure(
            ...     components=[component1, component2],
            ...     connections=[connection1],
            ...     standalone_elements=[]
            ... )
            >>> description = generator.generate_description(structure)
            >>> print(description)
            'The diagram contains a rectangle labeled "Google" and a rectangle labeled "Facebook". 
             "Google" connects to "Facebook".'
        """
        description_parts = []
        
        # Add diagram overview for detailed format only
        if self.format_style == "detailed" and (structure.components or structure.connections or structure.standalone_elements):
            overview = self._generate_overview(structure)
            if overview:
                description_parts.append(overview)
        
        # Describe components (labeled shapes)
        if structure.components:
            components_desc = self._describe_components(structure.components)
            if components_desc:
                description_parts.append(components_desc)
        
        # Describe connections between components
        if structure.connections:
            connections_desc = self._describe_connections(structure.connections)
            if connections_desc:
                description_parts.append(connections_desc)
        
        # Describe standalone elements
        if structure.standalone_elements:
            standalone_desc = self._describe_standalone_elements(structure.standalone_elements)
            if standalone_desc:
                description_parts.append(standalone_desc)
        
        # Combine all parts
        if not description_parts:
            return "The diagram appears to be empty or contains no recognizable elements."
        
        return " ".join(description_parts)
    
    def generate(self, structure: DiagramStructure) -> str:
        """
        Generate natural language description from diagram structure.
        
        This method implements the OutputGenerator interface by delegating
        to the existing generate_description method.
        
        Args:
            structure (DiagramStructure): Structured diagram data.
        
        Returns:
            str: Natural language description of the diagram.
        """
        return self.generate_description(structure)
    
    def get_supported_format(self) -> OutputFormat:
        """Get the output format supported by this generator.
        
        Returns:
            OutputFormat.DESCRIPTION for natural language descriptions
        """
        return OutputFormat.DESCRIPTION
    
    def get_format_name(self) -> str:
        """
        Get the name of this output format.
        
        Returns:
            str: Format name for natural language descriptions.
        """
        return "Natural Language"
    
    def get_supported_features(self) -> Dict[str, bool]:
        """
        Get information about supported features for natural language generation.
        
        Returns:
            Dict[str, bool]: Dictionary of supported features.
        """
        return {
            "components": True,
            "connections": True,
            "standalone_elements": True,
            "bidirectional_connections": True,
            "nested_structures": False,
            "styling": False,
            "positioning": self.include_positions
        }
    
    def _generate_overview(self, structure: DiagramStructure) -> str:
        """
        Generate a high-level overview of the diagram structure.
        
        Args:
            structure: DiagramStructure object
            
        Returns:
            Overview description string
        """
        if self.format_style != "detailed":
            return ""
        
        total_components = len(structure.components)
        total_connections = len(structure.connections)
        total_standalone = len(structure.standalone_elements)
        
        if total_components == 0 and total_connections == 0 and total_standalone == 0:
            return ""
        
        overview_parts = []
        
        if total_components > 0:
            if total_components == 1:
                overview_parts.append("1 main component")
            else:
                overview_parts.append(f"{total_components} main components")
        
        if total_connections > 0:
            if total_connections == 1:
                overview_parts.append("1 connection")
            else:
                overview_parts.append(f"{total_connections} connections")
        
        if total_standalone > 0:
            if total_standalone == 1:
                overview_parts.append("1 standalone element")
            else:
                overview_parts.append(f"{total_standalone} standalone elements")
        
        if len(overview_parts) == 1:
            return f"This diagram contains {overview_parts[0]}."
        elif len(overview_parts) == 2:
            return f"This diagram contains {overview_parts[0]} and {overview_parts[1]}."
        else:
            overview_list = ", ".join(overview_parts[:-1])
            return f"This diagram contains {overview_list}, and {overview_parts[-1]}."

    def _describe_components(self, components: List[Component]) -> str:
        """
        Describes labeled shapes in the diagram.
        
        Args:
            components: List of Component objects
            
        Returns:
            Natural language description of components
        """
        if not components:
            return ""
        
        component_descriptions = []
        
        for component in components:
            # Get component label text
            label_text = ""
            if component.label and component.label.text.strip():
                import re
                label_text = re.sub(r'\s+', ' ', component.label.text.strip())
            
            # Describe the component based on its shape type
            shape_type = self._get_shape_description(component.shape)
            
            # Build component description with optional position info
            if label_text:
                desc = f'a {shape_type} labeled "{label_text}"'
            else:
                desc = f"an unlabeled {shape_type}"
            
            # Add position information if requested
            if self.include_positions:
                x, y = component.position
                desc += f" at position ({x:.0f}, {y:.0f})"
            
            component_descriptions.append(desc)
        
        # Format the list of components based on style
        if self.format_style == "concise":
            if len(component_descriptions) <= 3:
                return self._format_component_list(component_descriptions, "The diagram has")
            else:
                return f"The diagram has {len(component_descriptions)} components including {component_descriptions[0]}, {component_descriptions[1]}, and others."
        else:
            return self._format_component_list(component_descriptions, "The diagram contains")
    
    def _format_component_list(self, descriptions: List[str], prefix: str) -> str:
        """Format a list of component descriptions with proper grammar."""
        if len(descriptions) == 1:
            return f"{prefix} {descriptions[0]}."
        elif len(descriptions) == 2:
            return f"{prefix} {descriptions[0]} and {descriptions[1]}."
        else:
            # Multiple components
            components_list = ", ".join(descriptions[:-1])
            return f"{prefix} {components_list}, and {descriptions[-1]}."

    def _describe_connections(self, connections: List[Connection]) -> str:
        """
        Describes arrow relationships between components using natural language.
        
        Args:
            connections: List of Connection objects
            
        Returns:
            Natural language description of connections
        """
        if not connections:
            return ""
        
        # Group connections by source-target pairs to detect bidirectional connections
        connection_pairs = {}
        for connection in connections:
            source_id = connection.source_component.shape.id
            target_id = connection.target_component.shape.id
            
            pair_key = tuple(sorted([source_id, target_id]))
            if pair_key not in connection_pairs:
                connection_pairs[pair_key] = []
            connection_pairs[pair_key].append(connection)
        
        connection_descriptions = []
        processed_connections = set()
        
        for connection in connections:
            if id(connection) in processed_connections:
                continue
            
            source_label = self._get_component_label(connection.source_component)
            target_label = self._get_component_label(connection.target_component)
            
            # Check for bidirectional connection
            source_id = connection.source_component.shape.id
            target_id = connection.target_component.shape.id
            pair_key = tuple(sorted([source_id, target_id]))
            pair_connections = connection_pairs[pair_key]
            
            if len(pair_connections) > 1:
                # Bidirectional connection
                template = self._get_direction_template("bidirectional")
                connection_desc = template.format(source=source_label, target=target_label)
                # Mark all connections in this pair as processed
                for conn in pair_connections:
                    processed_connections.add(id(conn))
            else:
                # Unidirectional connection
                direction_template = self._get_direction_template(connection.direction)
                connection_desc = direction_template.format(
                    source=source_label,
                    target=target_label
                )
                processed_connections.add(id(connection))
            
            connection_descriptions.append(connection_desc)
        
        # Limit detailed descriptions for large numbers of connections
        if len(connection_descriptions) > self.max_connections_detail:
            if self.format_style == "concise":
                return f"The diagram shows {len(connection_descriptions)} connections between components."
            else:
                detailed_count = self.max_connections_detail
                sample_connections = connection_descriptions[:detailed_count]
                remaining = len(connection_descriptions) - detailed_count
                
                formatted_sample = self._format_connection_list(sample_connections)
                return f"{formatted_sample} Additionally, there are {remaining} more connections in the diagram."
        
        return self._format_connection_list(connection_descriptions)
    
    def _format_connection_list(self, descriptions: List[str]) -> str:
        """Format a list of connection descriptions with proper grammar."""
        if len(descriptions) == 1:
            return descriptions[0] + "."
        elif len(descriptions) == 2:
            return f"{descriptions[0]}, and {descriptions[1]}."
        else:
            # Multiple connections
            connections_list = ", ".join(descriptions[:-1])
            return f"{connections_list}, and {descriptions[-1]}."

    def _describe_standalone_elements(self, elements: List[BaseElement]) -> str:
        """
        Describes unconnected components in the diagram.
        
        Args:
            elements: List of standalone BaseElement objects
            
        Returns:
            Natural language description of standalone elements
        """
        if not elements:
            return ""
        
        standalone_descriptions = []
        
        for element in elements:
            if isinstance(element, TextElement):
                # Only include text elements that have non-empty content
                if element.text.strip():
                    import re
                    normalized_text = re.sub(r'\s+', ' ', element.text.strip())
                    standalone_descriptions.append(f'standalone text "{normalized_text}"')
                # Skip text elements with empty or whitespace-only content
            elif isinstance(element, RectangleElement):
                standalone_descriptions.append("a standalone rectangle")
            elif isinstance(element, ArrowElement):
                standalone_descriptions.append("a standalone arrow")
            else:
                # Generic description for other element types
                element_type = element.type.replace("_", " ")
                standalone_descriptions.append(f"a standalone {element_type}")
        
        # Format the list of standalone elements
        if not standalone_descriptions:
            return ""
        
        if len(standalone_descriptions) == 1:
            return f"Additionally, there is {standalone_descriptions[0]}."
        elif len(standalone_descriptions) == 2:
            return f"Additionally, there are {standalone_descriptions[0]} and {standalone_descriptions[1]}."
        else:
            # Multiple standalone elements
            elements_list = ", ".join(standalone_descriptions[:-1])
            return f"Additionally, there are {elements_list}, and {standalone_descriptions[-1]}."

    def _get_component_label(self, component: Component) -> str:
        """
        Gets a descriptive label for a component.
        
        Args:
            component: Component object
            
        Returns:
            Descriptive label for the component
        """
        if component.label and component.label.text.strip():
            import re
            normalized_text = re.sub(r'\s+', ' ', component.label.text.strip())
            return f'"{normalized_text}"'
        else:
            shape_type = self._get_shape_description(component.shape)
            return f"the {shape_type}"

    def _get_shape_description(self, shape: BaseElement) -> str:
        """
        Gets a human-readable description of a shape type with variety.
        
        Args:
            shape: BaseElement representing the shape
            
        Returns:
            Human-readable shape description
        """
        shape_type = shape.type.lower()
        
        # Use varied descriptions based on format style
        if shape_type in self._shape_descriptions:
            descriptions = self._shape_descriptions[shape_type]
            if self.format_style == "technical":
                return descriptions[0]  # Use most precise term
            elif self.format_style == "concise":
                return descriptions[0]  # Use shortest term
            elif self.format_style == "detailed":
                # For detailed format, use some variety
                import random
                return random.choice(descriptions)
            else:
                # Standard format - use consistent terminology
                return descriptions[0]
        
        # Handle specific element types
        if isinstance(shape, RectangleElement):
            if self.format_style == "detailed":
                import random
                return random.choice(self._shape_descriptions["rectangle"])
            else:
                return "rectangle"
        elif shape_type == "ellipse":
            if self.format_style == "detailed":
                import random
                return random.choice(self._shape_descriptions["ellipse"])
            else:
                return "circle"
        elif shape_type == "diamond":
            if self.format_style == "detailed":
                import random
                return random.choice(self._shape_descriptions["diamond"])
            else:
                return "diamond"
        else:
            # Generic description for unknown shapes
            return shape.type.replace("_", " ")

    def _get_direction_template(self, direction: str) -> str:
        """
        Gets natural language template for connection direction with variety.
        
        Args:
            direction: Direction string (e.g., "left-to-right")
            
        Returns:
            Natural language template with {source} and {target} placeholders
        """
        if direction in self._connection_templates:
            templates = self._connection_templates[direction]
            if self.format_style == "technical":
                return templates[0]  # Use most precise template
            elif self.format_style == "concise":
                return templates[0]  # Use shortest template
            elif self.format_style == "detailed":
                # For detailed format, use variety
                import random
                return random.choice(templates)
            else:
                # Standard format - use consistent terminology
                return templates[0]
        
        # Fallback for unknown directions
        return "{source} is connected to {target}"