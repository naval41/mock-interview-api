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
    - Group relationships (elements with same groupIds)
    - Text-container relationships (text inside shapes)
    - Arrow connections between components
    - Spatial containment and positioning
    
    The analyzer processes a flat list of elements and organizes them into a
    hierarchical structure of components, connections, and standalone elements
    that better represents the logical structure of the diagram.
    
    Key capabilities:
        - Groups elements with same groupIds into single logical units
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
        1. Group elements by their groupIds (treat grouped elements as single units)
        2. Find text-container relationships (text inside shapes)
        3. Create components from shapes and their associated text
        4. Detect arrow connections between components
        5. Identify standalone elements not part of any relationship
        
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
        # Group elements by their groupIds
        element_groups = self._group_elements_by_group_ids(elements)
        
        # Find text-container relationships (considering groups)
        text_containers = self._find_text_containers_with_groups(elements, element_groups)
        
        # Create components from shapes and their associated text (considering groups)
        components = self._create_components_with_groups(elements, text_containers, element_groups)
        
        # Find arrow connections between components
        connections = self._find_arrow_connections(elements, components)
        
        # Identify standalone elements (not part of components or connections)
        standalone_elements = self._identify_standalone_elements_with_groups(elements, components, connections, element_groups)
        
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
        # Check if text has bound_elements pointing to containers
        if text_element.bound_elements:
            for bound in text_element.bound_elements:
                bound_id = bound.get('id')
                # Check if this bound element is a container
                for container in container_elements:
                    if container.id == bound_id:
                        return container.id
        
        # Also check reverse relationship: containers that have this text in their boundElements
        for container in container_elements:
            if hasattr(container, 'bound_elements') and container.bound_elements:
                for bound in container.bound_elements:
                    if bound.get('id') == text_element.id and bound.get('type') == 'text':
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
        
        # Create mapping of element ID to component (including grouped elements)
        element_to_component = {}
        for component in components:
            # Map the primary shape
            element_to_component[component.shape.id] = component
            
            # If the component's shape has group_ids, map all elements in those groups to this component
            if hasattr(component.shape, 'group_ids') and component.shape.group_ids:
                for group_id in component.shape.group_ids:
                    # Find all elements with this group_id
                    for element in elements:
                        if (hasattr(element, 'group_ids') and element.group_ids and 
                            group_id in element.group_ids):
                            element_to_component[element.id] = component
        
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

    def _group_elements_by_group_ids(self, elements: List[BaseElement]) -> Dict[str, List[BaseElement]]:
        """
        Groups elements by their groupIds to treat them as single logical units.
        
        When elements belong to multiple groups, we prefer groups that contain
        both text and shape elements (more meaningful relationships).
        
        Args:
            elements: List of all elements
            
        Returns:
            Dictionary mapping group ID to list of elements in that group
        """
        # First, collect all elements for each group
        all_groups = {}
        for element in elements:
            if hasattr(element, 'group_ids') and element.group_ids:
                for group_id in element.group_ids:
                    if group_id not in all_groups:
                        all_groups[group_id] = []
                    all_groups[group_id].append(element)
        
        # Find the best group for each element (prefer groups with mixed element types)
        element_to_best_group = {}
        
        for element in elements:
            if hasattr(element, 'group_ids') and element.group_ids:
                best_group = None
                best_score = -1
                
                for group_id in element.group_ids:
                    group_elements = all_groups[group_id]
                    
                    # Calculate score based on group composition
                    has_text = any(hasattr(e, 'text') for e in group_elements)
                    has_shape = any(e.type in ['rectangle', 'ellipse', 'diamond'] for e in group_elements)
                    
                    # Prefer groups with both text and shapes
                    score = 0
                    if has_text and has_shape:
                        score = 100  # Highest priority for mixed groups
                    elif has_text or has_shape:
                        score = 50   # Medium priority for single-type groups
                    
                    # Prefer smaller, more specific groups
                    score -= len(group_elements)
                    
                    if score > best_score:
                        best_score = score
                        best_group = group_id
                
                if best_group:
                    element_to_best_group[element.id] = best_group
        
        # Build final groups using best group assignments
        element_groups = {}
        for element in elements:
            if element.id in element_to_best_group:
                group_id = element_to_best_group[element.id]
                if group_id not in element_groups:
                    element_groups[group_id] = []
                element_groups[group_id].append(element)
        
        return element_groups

    def _find_text_containers_with_groups(self, elements: List[BaseElement], 
                                        element_groups: Dict[str, List[BaseElement]]) -> Dict[str, str]:
        """
        Associates text elements with their container shapes, considering groups.
        
        Args:
            elements: List of all elements
            element_groups: Dictionary of grouped elements
            
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
            
            # Check if text and container are in the same group
            container_id = self._find_container_in_same_group(text_element, container_elements, element_groups)
            if container_id:
                text_containers[text_element.id] = container_id
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

    def _find_container_in_same_group(self, text_element: TextElement, 
                                    container_elements: List[BaseElement],
                                    element_groups: Dict[str, List[BaseElement]]) -> Optional[str]:
        """
        Find container element that's in the same group as the text element.
        
        Args:
            text_element: Text element to find container for
            container_elements: List of potential container elements
            element_groups: Dictionary of grouped elements
            
        Returns:
            Container element ID if found, None otherwise
        """
        if not hasattr(text_element, 'group_ids') or not text_element.group_ids:
            return None
        
        # Get the primary group ID for the text element
        text_group_id = text_element.group_ids[0]
        
        # Check if this group exists and has container elements
        if text_group_id in element_groups:
            group_elements = element_groups[text_group_id]
            
            # Find container elements in the same group
            for element in group_elements:
                if element in container_elements and element.id != text_element.id:
                    return element.id
        
        return None

    def _create_components_with_groups(self, elements: List[BaseElement], 
                                     text_containers: Dict[str, str],
                                     element_groups: Dict[str, List[BaseElement]]) -> List[Component]:
        """
        Creates Component objects from shapes and their associated text, considering groups.
        
        When elements are grouped, the entire group is treated as a single component.
        The primary shape (usually the largest or first rectangle) becomes the component shape,
        and all text elements in the group become potential labels.
        
        Args:
            elements: All elements
            text_containers: Mapping of text ID to container ID
            element_groups: Dictionary of grouped elements
            
        Returns:
            List of Component objects
        """
        components = []
        processed_elements = set()
        
        # First, process grouped elements
        for group_id, group_elements in element_groups.items():
            if not group_elements:
                continue
                
            # Find the primary shape in the group (prefer rectangles, then largest element)
            shape_elements = [e for e in group_elements if isinstance(e, (RectangleElement,)) or 
                            (isinstance(e, BaseElement) and e.type in ['ellipse', 'diamond', 'triangle', 'hexagon'])]
            
            if not shape_elements:
                continue
            
            # Choose primary shape (largest rectangle or first shape)
            primary_shape = self._choose_primary_shape(shape_elements)
            
            # Find all text elements in the group
            text_elements = [e for e in group_elements if isinstance(e, TextElement)]
            
            # Choose primary label (first non-empty text or text with most content)
            primary_label = self._choose_primary_label(text_elements)
            
            # Calculate group bounds for position and size
            group_bounds = self._calculate_group_bounds(group_elements)
            
            component = Component(
                shape=primary_shape,
                label=primary_label,
                position=group_bounds['position'],
                size=group_bounds['size']
            )
            components.append(component)
            
            # Mark all group elements as processed
            for element in group_elements:
                processed_elements.add(element.id)
        
        # Then, process individual (non-grouped) elements
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
            # Skip if already processed as part of a group
            if shape.id in processed_elements:
                continue
                
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

    def _choose_primary_shape(self, shape_elements: List[BaseElement]) -> BaseElement:
        """
        Choose the primary shape from a group of shapes.
        
        Prefers rectangles, then chooses the largest element by area.
        
        Args:
            shape_elements: List of shape elements in the group
            
        Returns:
            Primary shape element
        """
        if not shape_elements:
            return shape_elements[0]
        
        # Prefer rectangles
        rectangles = [e for e in shape_elements if isinstance(e, RectangleElement)]
        if rectangles:
            # Choose largest rectangle by area
            return max(rectangles, key=lambda e: e.width * e.height)
        
        # Otherwise, choose largest element by area
        return max(shape_elements, key=lambda e: e.width * e.height)

    def _choose_primary_label(self, text_elements: List[TextElement]) -> Optional[TextElement]:
        """
        Choose the primary label from a group of text elements.
        
        Prefers non-empty text, then chooses the text with most content.
        
        Args:
            text_elements: List of text elements in the group
            
        Returns:
            Primary text element or None if no suitable text found
        """
        if not text_elements:
            return None
        
        # Filter out empty text elements
        non_empty_texts = [e for e in text_elements if e.text.strip()]
        if not non_empty_texts:
            return text_elements[0] if text_elements else None
        
        # Choose text with most content
        return max(non_empty_texts, key=lambda e: len(e.text.strip()))

    def _calculate_group_bounds(self, group_elements: List[BaseElement]) -> Dict[str, tuple]:
        """
        Calculate the bounding box for a group of elements.
        
        Args:
            group_elements: List of elements in the group
            
        Returns:
            Dictionary with 'position' and 'size' tuples
        """
        if not group_elements:
            return {'position': (0, 0), 'size': (0, 0)}
        
        # Calculate bounding box
        min_x = min(e.x for e in group_elements)
        min_y = min(e.y for e in group_elements)
        max_x = max(e.x + e.width for e in group_elements)
        max_y = max(e.y + e.height for e in group_elements)
        
        return {
            'position': (min_x, min_y),
            'size': (max_x - min_x, max_y - min_y)
        }

    def _identify_standalone_elements_with_groups(self, elements: List[BaseElement],
                                                components: List[Component],
                                                connections: List[Connection],
                                                element_groups: Dict[str, List[BaseElement]]) -> List[BaseElement]:
        """
        Identifies elements that are not part of any component or connection, considering groups.
        
        Args:
            elements: All elements
            components: List of components
            connections: List of connections
            element_groups: Dictionary of grouped elements
            
        Returns:
            List of standalone elements
        """
        # Collect IDs of elements that are part of components or connections
        used_element_ids: Set[str] = set()
        
        # Add all elements from groups that were used to create components
        for group_id, group_elements in element_groups.items():
            # Check if this group was used to create a component
            group_used = False
            for component in components:
                # Check if the component's shape is from this group
                if hasattr(component.shape, 'group_ids') and component.shape.group_ids and group_id in component.shape.group_ids:
                    group_used = True
                    break
            
            # If group was used, mark all its elements as used
            if group_used:
                for element in group_elements:
                    used_element_ids.add(element.id)
        
        # Add component shape and label IDs for non-grouped components
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