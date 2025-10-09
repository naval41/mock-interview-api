"""
Relationship analysis for Excalidraw elements.
"""

from typing import List, Dict, Optional, Set
from .models import (
    BaseElement, TextElement, ArrowElement, RectangleElement,
    Component, Connection, DiagramStructure
)


class RelationshipAnalyzer:
    """
    Analyzes relationships between Excalidraw elements to build diagram structure.
    
    This class identifies various types of relationships between elements:
    - Text-container relationships (text inside shapes)
    - Arrow connections between components
    - Spatial containment and positioning
    
    The analyzer processes a flat list of elements and organizes them into a
    hierarchical structure of components, connections, and standalone elements
    that better represents the logical structure of the diagram.
    
    Key capabilities:
        - Associates text elements with their container shapes
        - Detects arrow connections and their directionality
        - Identifies standalone elements not part of any relationship
        - Handles both explicit bindings and spatial relationships
    
    Example:
        >>> analyzer = RelationshipAnalyzer()
        >>> elements = [rectangle_elem, text_elem, arrow_elem]
        >>> structure = analyzer.analyze_relationships(elements)
        >>> print(f"Found {len(structure.components)} components")
        >>> print(f"Found {len(structure.connections)} connections")
    """

    def analyze_relationships(self, elements: List[BaseElement]) -> DiagramStructure:
        """
        Analyzes all relationships between elements and returns structured diagram data.
        
        This is the main entry point for relationship analysis. It processes elements
        in multiple passes to identify different types of relationships and build
        a comprehensive diagram structure.
        
        Processing steps:
        1. Find text-container relationships (text inside shapes)
        2. Create components from shapes and their associated text
        3. Detect arrow connections between components
        4. Identify standalone elements not part of any relationship
        
        Args:
            elements (List[BaseElement]): List of parsed Excalidraw elements including
                rectangles, text, arrows, and other element types.
        
        Returns:
            DiagramStructure: Structured representation containing:
                - components: List of Component objects (shapes with optional text labels)
                - connections: List of Connection objects (arrows between components)
                - standalone_elements: List of elements not part of any relationship
        
        Example:
            >>> elements = [rect1, text1, arrow1, rect2, text2]
            >>> structure = analyzer.analyze_relationships(elements)
            >>> # Access components
            >>> for component in structure.components:
            ...     print(f"Component: {component.label.text if component.label else 'unlabeled'}")
            >>> # Access connections
            >>> for connection in structure.connections:
            ...     print(f"Connection: {connection.direction}")
        """
        # Find text-container relationships
        text_containers = self._find_text_containers(elements)
        
        # Create components from shapes and their associated text
        components = self._create_components(elements, text_containers)
        
        # Find arrow connections between components
        connections = self._find_arrow_connections(elements, components)
        
        # Identify standalone elements (not part of components or connections)
        standalone_elements = self._identify_standalone_elements(elements, components, connections)
        
        return DiagramStructure(
            components=components,
            connections=connections,
            standalone_elements=standalone_elements
        )

    def _find_text_containers(self, elements: List[BaseElement]) -> Dict[str, str]:
        """
        Associates text elements with their container shapes.
        
        Args:
            elements: List of all elements
            
        Returns:
            Dictionary mapping text element ID to container element ID
        """
        text_containers = {}
        
        # Get all text elements
        text_elements = [e for e in elements if isinstance(e, TextElement)]
        
        # Get all potential container elements (rectangles, etc.)
        container_elements = [e for e in elements if isinstance(e, RectangleElement)]
        
        for text_element in text_elements:
            # Check if text has explicit container_id
            if text_element.container_id:
                text_containers[text_element.id] = text_element.container_id
                continue
            
            # Check bound_elements for container relationship
            container_id = self._find_container_from_bounds(text_element, container_elements)
            if container_id:
                text_containers[text_element.id] = container_id
                continue
                
            # Check spatial containment (text inside shape boundaries)
            container_id = self._find_container_by_position(text_element, container_elements)
            if container_id:
                text_containers[text_element.id] = container_id
        
        return text_containers

    def _find_container_from_bounds(self, text_element: TextElement, 
                                  container_elements: List[BaseElement]) -> Optional[str]:
        """Find container from bound_elements relationships."""
        if not text_element.bound_elements:
            return None
            
        for bound in text_element.bound_elements:
            if bound.get('type') == 'text':
                bound_id = bound.get('id')
                # Check if this bound element is a container
                for container in container_elements:
                    if container.id == bound_id:
                        return container.id
        return None

    def _find_container_by_position(self, text_element: TextElement,
                                  container_elements: List[BaseElement]) -> Optional[str]:
        """Find container by checking if text is spatially inside a shape."""
        text_center_x = text_element.x + text_element.width / 2
        text_center_y = text_element.y + text_element.height / 2
        
        for container in container_elements:
            # Check if text center is within container bounds
            if (container.x <= text_center_x <= container.x + container.width and
                container.y <= text_center_y <= container.y + container.height):
                return container.id
        
        return None

    def _create_components(self, elements: List[BaseElement], 
                          text_containers: Dict[str, str]) -> List[Component]:
        """
        Creates Component objects from shapes and their associated text.
        
        Args:
            elements: All elements
            text_containers: Mapping of text ID to container ID
            
        Returns:
            List of Component objects
        """
        components = []
        
        # Get all shape elements that can be components (rectangles and other shape types)
        shape_elements = [e for e in elements if isinstance(e, (RectangleElement,)) or 
                         (isinstance(e, BaseElement) and e.type in ['ellipse', 'diamond', 'triangle', 'hexagon'])]
        
        # Create reverse mapping: container_id -> text_elements
        container_texts = {}
        for text_id, container_id in text_containers.items():
            if container_id not in container_texts:
                container_texts[container_id] = []
            # Find the text element
            text_element = next((e for e in elements if e.id == text_id), None)
            if text_element:
                container_texts[container_id].append(text_element)
        
        for shape in shape_elements:
            # Find associated text (use first text if multiple)
            label = None
            if shape.id in container_texts and container_texts[shape.id]:
                label = container_texts[shape.id][0]  # Use first text as primary label
            
            component = Component(
                shape=shape,
                label=label,
                position=(shape.x, shape.y),
                size=(shape.width, shape.height)
            )
            components.append(component)
        
        return components

    def _find_arrow_connections(self, elements: List[BaseElement], 
                              components: List[Component]) -> List[Connection]:
        """
        Detects arrow connections between components.
        
        Args:
            elements: All elements
            components: List of components
            
        Returns:
            List of Connection objects
        """
        connections = []
        
        # Get all arrow elements
        arrow_elements = [e for e in elements if isinstance(e, ArrowElement)]
        
        # Create mapping of element ID to component
        element_to_component = {}
        for component in components:
            element_to_component[component.shape.id] = component
        
        for arrow in arrow_elements:
            source_component = None
            target_component = None
            
            # Find source component
            if arrow.start_binding and arrow.start_binding.element_id:
                source_component = element_to_component.get(arrow.start_binding.element_id)
            
            # Find target component
            if arrow.end_binding and arrow.end_binding.element_id:
                target_component = element_to_component.get(arrow.end_binding.element_id)
            
            # Only create connection if both source and target are found
            if source_component and target_component:
                direction = self._determine_arrow_direction(arrow, source_component, target_component)
                
                connection = Connection(
                    source_component=source_component,
                    target_component=target_component,
                    arrow=arrow,
                    direction=direction
                )
                connections.append(connection)
        
        return connections

    def _determine_arrow_direction(self, arrow: ArrowElement, 
                                 source_component: Component, 
                                 target_component: Component) -> str:
        """
        Determines the direction of an arrow connection.
        
        Args:
            arrow: Arrow element
            source_component: Source component
            target_component: Target component
            
        Returns:
            Direction string (e.g., "left-to-right", "top-to-bottom")
        """
        source_center_x = source_component.position[0] + source_component.size[0] / 2
        source_center_y = source_component.position[1] + source_component.size[1] / 2
        target_center_x = target_component.position[0] + target_component.size[0] / 2
        target_center_y = target_component.position[1] + target_component.size[1] / 2
        
        dx = target_center_x - source_center_x
        dy = target_center_y - source_center_y
        
        # Determine primary direction based on larger displacement
        if abs(dx) > abs(dy):
            return "left-to-right" if dx > 0 else "right-to-left"
        else:
            return "top-to-bottom" if dy > 0 else "bottom-to-top"

    def _identify_standalone_elements(self, elements: List[BaseElement],
                                    components: List[Component],
                                    connections: List[Connection]) -> List[BaseElement]:
        """
        Identifies elements that are not part of any component or connection.
        
        Args:
            elements: All elements
            components: List of components
            connections: List of connections
            
        Returns:
            List of standalone elements
        """
        # Collect IDs of elements that are part of components or connections
        used_element_ids: Set[str] = set()
        
        # Add component shape and label IDs
        for component in components:
            used_element_ids.add(component.shape.id)
            if component.label:
                used_element_ids.add(component.label.id)
        
        # Add connection arrow IDs
        for connection in connections:
            used_element_ids.add(connection.arrow.id)
        
        # Find elements not in the used set
        standalone_elements = []
        for element in elements:
            if element.id not in used_element_ids:
                standalone_elements.append(element)
        
        return standalone_elements