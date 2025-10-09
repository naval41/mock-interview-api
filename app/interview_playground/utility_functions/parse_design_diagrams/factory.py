"""
Element factory for creating Excalidraw elements from JSON data.
"""

import json
from typing import Dict, Any, Union, List, Tuple, Optional

from .models import BaseElement, RectangleElement, TextElement, ArrowElement, ElementBinding
from .exceptions import JSONParseError, ValidationError, ElementProcessingError


class ElementFactory:
    """
    Factory class for creating Excalidraw elements from JSON data.
    
    This factory handles the conversion of raw JSON element data into strongly-typed
    Python objects. It supports various Excalidraw element types and provides
    comprehensive validation and error handling.
    
    The factory automatically detects element types and creates appropriate subclasses
    of BaseElement. For unsupported element types, it gracefully falls back to
    creating BaseElement instances.
    
    Supported element types:
        - rectangle: Creates RectangleElement instances
        - text: Creates TextElement instances with text content and formatting
        - arrow: Creates ArrowElement instances with binding information
        - others: Creates BaseElement instances for unknown types
    
    Example:
        >>> factory = ElementFactory()
        >>> element_data = {
        ...     "id": "rect1",
        ...     "type": "rectangle",
        ...     "x": 100, "y": 200,
        ...     "width": 150, "height": 100
        ... }
        >>> element = factory.create_element(element_data)
        >>> isinstance(element, RectangleElement)
        True
    """
    
    # Supported element types mapping
    ELEMENT_TYPE_MAPPING = {
        'rectangle': '_create_rectangle',
        'text': '_create_text', 
        'arrow': '_create_arrow',
    }
    
    def create_element(self, element_data: Union[Dict[str, Any], str]) -> BaseElement:
        """
        Create an appropriate element instance from JSON data.
        
        This is the main factory method that analyzes the element type and delegates
        to the appropriate specialized creation method. It handles JSON parsing,
        validation, and error recovery.
        
        Args:
            element_data (Union[Dict[str, Any], str]): Element data as either:
                - Dictionary: Pre-parsed element data with required fields
                - JSON string: Raw JSON string representing a single element
        
        Returns:
            BaseElement: Appropriate element subclass instance:
                - RectangleElement for "rectangle" type
                - TextElement for "text" type  
                - ArrowElement for "arrow" type
                - BaseElement for unknown/unsupported types
        
        Raises:
            JSONParseError: If the input JSON string cannot be parsed. Includes
                the original JSON content and line number information when available.
            ValidationError: If required fields (id, type, x, y, width, height) are
                missing or have invalid types. Includes field name and element context.
            ElementProcessingError: If element creation fails due to data inconsistencies
                or unexpected errors during processing.
        
        Example:
            >>> factory = ElementFactory()
            >>> # From dictionary
            >>> rect = factory.create_element({
            ...     "id": "rect1", "type": "rectangle",
            ...     "x": 0, "y": 0, "width": 100, "height": 50
            ... })
            >>> # From JSON string
            >>> text = factory.create_element('{"id": "text1", "type": "text", "text": "Hello"}')
        """
        # Handle string input by parsing JSON
        if isinstance(element_data, str):
            try:
                element_data = json.loads(element_data)
            except json.JSONDecodeError as e:
                raise JSONParseError(
                    f"Failed to parse JSON: {str(e)}", 
                    json_content=element_data,
                    line_number=getattr(e, 'lineno', None)
                )
        
        # Validate input is a dictionary
        if not isinstance(element_data, dict):
            raise ValidationError(
                "Element data must be a dictionary or valid JSON string",
                field_value=type(element_data).__name__
            )
        
        # Extract and validate element type
        element_type = element_data.get('type')
        element_id = element_data.get('id', 'unknown')
        
        if not element_type:
            raise ValidationError(
                "Element type is required",
                field_name='type',
                element_id=element_id
            )
        
        if not isinstance(element_type, str):
            raise ValidationError(
                "Element type must be a string",
                field_name='type',
                field_value=element_type,
                element_id=element_id
            )
        
        # Get factory method for element type
        factory_method_name = self.ELEMENT_TYPE_MAPPING.get(element_type.lower())
        
        if not factory_method_name:
            # Handle unsupported element types gracefully
            # Log this as debug information (logging will be added if needed)
            return self._create_base_element(element_data)
        
        try:
            factory_method = getattr(self, factory_method_name)
            return factory_method(element_data)
        except Exception as e:
            if isinstance(e, (ValidationError, ElementProcessingError)):
                raise
            raise ElementProcessingError(
                f"Failed to create {element_type} element: {str(e)}",
                element_id=element_id,
                element_type=element_type,
                element_data=element_data
            )
    
    def _create_base_element(self, data: Dict[str, Any]) -> BaseElement:
        """Create a base element for unsupported types.
        
        Args:
            data: Element data dictionary
            
        Returns:
            BaseElement: Base element instance
        """
        return BaseElement(**self._extract_base_fields(data))
    
    def _create_rectangle(self, data: Dict[str, Any]) -> RectangleElement:
        """Create a rectangle element from JSON data.
        
        Args:
            data: Element data dictionary
            
        Returns:
            RectangleElement: Rectangle element instance
        """
        base_fields = self._extract_base_fields(data)
        return RectangleElement(**base_fields)
    
    def _create_text(self, data: Dict[str, Any]) -> TextElement:
        """Create a text element from JSON data.
        
        Args:
            data: Element data dictionary
            
        Returns:
            TextElement: Text element instance
        """
        base_fields = self._extract_base_fields(data)
        
        # Extract text-specific fields
        text_fields = {
            'text': self._extract_field(data, 'text', str, default=''),
            'font_size': self._extract_field(data, 'fontSize', (int, float), default=20),
            'font_family': self._extract_field(data, 'fontFamily', int, default=1),
            'text_align': self._extract_field(data, 'textAlign', str, default='left'),
            'vertical_align': self._extract_field(data, 'verticalAlign', str, default='top'),
            'line_height': self._extract_field(data, 'lineHeight', (int, float), default=1.25),
            'original_text': self._extract_field(data, 'originalText', str, default=''),
        }
        
        # Handle container binding
        container_id = None
        if 'containerId' in data and data['containerId']:
            container_id = str(data['containerId'])
        text_fields['container_id'] = container_id
        
        # Set original_text to text if not provided
        if not text_fields['original_text']:
            text_fields['original_text'] = text_fields['text']
        
        return TextElement(**{**base_fields, **text_fields})
    
    def _create_arrow(self, data: Dict[str, Any]) -> ArrowElement:
        """Create an arrow element from JSON data.
        
        Args:
            data: Element data dictionary
            
        Returns:
            ArrowElement: Arrow element instance
        """
        base_fields = self._extract_base_fields(data)
        
        # Extract arrow-specific fields
        arrow_fields = {
            'points': self._extract_points(data),
            'start_binding': self._extract_binding(data, 'startBinding'),
            'end_binding': self._extract_binding(data, 'endBinding'),
            'start_arrow_head': self._extract_field(data, 'startArrowhead', str, required=False),
            'end_arrow_head': self._extract_field(data, 'endArrowhead', str, default='arrow'),
        }
        
        # Extract last committed point
        last_point = data.get('lastCommittedPoint')
        if last_point and isinstance(last_point, (list, tuple)) and len(last_point) >= 2:
            arrow_fields['last_committed_point'] = (float(last_point[0]), float(last_point[1]))
        
        return ArrowElement(**{**base_fields, **arrow_fields})
    
    def _extract_base_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract common base element fields from JSON data.
        
        Args:
            data: Element data dictionary
            
        Returns:
            Dict[str, Any]: Dictionary of base element fields
        """
        element_id = self._extract_field(data, 'id', str, required=True)
        element_type = self._extract_field(data, 'type', str, required=True)
        
        return {
            'id': element_id,
            'type': element_type,
            'x': self._extract_field(data, 'x', (int, float), required=True),
            'y': self._extract_field(data, 'y', (int, float), required=True),
            'width': self._extract_field(data, 'width', (int, float), required=True),
            'height': self._extract_field(data, 'height', (int, float), required=True),
            'angle': self._extract_field(data, 'angle', (int, float), default=0.0),
            'stroke_color': self._extract_field(data, 'strokeColor', str, default='#000000'),
            'background_color': self._extract_field(data, 'backgroundColor', str, default='transparent'),
            'fill_style': self._extract_field(data, 'fillStyle', str, default='hachure'),
            'stroke_width': self._extract_field(data, 'strokeWidth', int, default=1),
            'stroke_style': self._extract_field(data, 'strokeStyle', str, default='solid'),
            'roughness': self._extract_field(data, 'roughness', int, default=1),
            'opacity': self._extract_field(data, 'opacity', int, default=100),
            'group_ids': self._extract_field(data, 'groupIds', list, default=[]),
            'frame_id': self._extract_field(data, 'frameId', str, required=False),
            'index': self._extract_field(data, 'index', str, default='a0'),
            'rounded_radius': self._extract_roundness(data),
            'bound_elements': self._extract_field(data, 'boundElements', list, default=[]),
            'updated': self._extract_field(data, 'updated', int, default=1),
            'link': self._extract_field(data, 'link', str, required=False),
            'locked': self._extract_field(data, 'locked', bool, default=False),
        }
    
    def _extract_field(self, data: Dict[str, Any], field_name: str, 
                      expected_type: Union[type, Tuple[type, ...]], 
                      required: bool = False, default: Any = None) -> Any:
        """Extract and validate a field from element data.
        
        Args:
            data: Element data dictionary
            field_name: Name of the field to extract
            expected_type: Expected type(s) for the field
            required: Whether the field is required
            default: Default value if field is missing
            
        Returns:
            Any: The extracted and validated field value
            
        Raises:
            ValidationError: If field validation fails
        """
        element_id = data.get('id', 'unknown')
        element_type = data.get('type', 'unknown')
        
        if field_name not in data:
            if required:
                raise ValidationError(
                    f"Required field '{field_name}' is missing",
                    field_name=field_name,
                    element_id=element_id,
                    element_type=element_type
                )
            return default
        
        value = data[field_name]
        
        # Handle None values
        if value is None:
            if required:
                raise ValidationError(
                    f"Required field '{field_name}' cannot be None",
                    field_name=field_name,
                    field_value=value,
                    element_id=element_id,
                    element_type=element_type
                )
            return default
        
        # Type validation
        if not isinstance(value, expected_type):
            raise ValidationError(
                f"Field '{field_name}' must be of type {expected_type}, got {type(value).__name__}",
                field_name=field_name,
                field_value=value,
                element_id=element_id,
                element_type=element_type
            )
        
        return value
    
    def _extract_points(self, data: Dict[str, Any]) -> List[Tuple[float, float]]:
        """Extract and validate points array for arrow elements.
        
        Args:
            data: Element data dictionary
            
        Returns:
            List[Tuple[float, float]]: List of point coordinates
        """
        element_id = data.get('id', 'unknown')
        points_data = data.get('points', [])
        
        if not isinstance(points_data, list):
            raise ValidationError(
                "Points must be a list",
                field_name='points',
                field_value=points_data,
                element_id=element_id,
                element_type='arrow'
            )
        
        points = []
        for i, point in enumerate(points_data):
            if not isinstance(point, (list, tuple)) or len(point) < 2:
                raise ValidationError(
                    f"Point at index {i} must be a list/tuple with at least 2 coordinates",
                    field_name=f'points[{i}]',
                    field_value=point,
                    element_id=element_id,
                    element_type='arrow'
                )
            
            try:
                x, y = float(point[0]), float(point[1])
                points.append((x, y))
            except (ValueError, TypeError) as e:
                raise ValidationError(
                    f"Point coordinates at index {i} must be numeric: {str(e)}",
                    field_name=f'points[{i}]',
                    field_value=point,
                    element_id=element_id,
                    element_type='arrow'
                )
        
        # Default to [(0, 0), (0, 0)] if no points provided
        if not points:
            points = [(0.0, 0.0), (0.0, 0.0)]
        
        return points
    
    def _extract_roundness(self, data: Dict[str, Any]) -> Optional[int]:
        """Extract roundness value, handling both integer and dictionary formats.
        
        Args:
            data: Element data dictionary
            
        Returns:
            Optional[int]: Roundness value or None
        """
        roundness = data.get('roundness')
        if roundness is None:
            return None
        
        # Handle dictionary format (newer Excalidraw versions)
        if isinstance(roundness, dict):
            # Extract the 'type' field from roundness object
            return roundness.get('type')
        
        # Handle integer format (older versions)
        if isinstance(roundness, (int, float)):
            return int(roundness)
        
        # Invalid format, return None
        return None
    
    def _extract_binding(self, data: Dict[str, Any], binding_field: str) -> Optional[ElementBinding]:
        """Extract and validate element binding data.
        
        Args:
            data: Element data dictionary
            binding_field: Name of the binding field ('startBinding' or 'endBinding')
            
        Returns:
            Optional[ElementBinding]: Element binding instance or None
        """
        binding_data = data.get(binding_field)
        if binding_data is None:
            return None
        
        element_id = data.get('id', 'unknown')
        
        if not isinstance(binding_data, dict):
            raise ValidationError(
                f"{binding_field} must be a dictionary",
                field_name=binding_field,
                field_value=binding_data,
                element_id=element_id,
                element_type='arrow'
            )
        
        try:
            return ElementBinding(
                element_id=self._extract_field(binding_data, 'elementId', str, required=True),
                focus=self._extract_field(binding_data, 'focus', (int, float), default=0.0),
                gap=self._extract_field(binding_data, 'gap', (int, float), default=0.0)
            )
        except ValidationError as e:
            # Re-raise with additional context
            raise ValidationError(
                f"Invalid {binding_field}: {e.message}",
                field_name=binding_field,
                element_id=element_id,
                element_type='arrow'
            )