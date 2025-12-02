"""
Data models for Excalidraw elements.
"""

from dataclasses import dataclass
from typing import Optional, List, Tuple, Any, Dict


@dataclass
class ElementBinding:
    """Represents a binding between elements (e.g., arrow endpoints)."""
    element_id: str
    focus: float
    gap: float


@dataclass
class BaseElement:
    """
    Base class for all Excalidraw elements with common properties.
    
    This class defines the common attributes shared by all Excalidraw elements
    including position, size, styling, and metadata. It serves as the foundation
    for specialized element types like rectangles, text, and arrows.
    
    Attributes:
        id (str): Unique identifier for the element
        type (str): Element type (rectangle, text, arrow, etc.)
        x (float): X coordinate of the element's top-left corner
        y (float): Y coordinate of the element's top-left corner
        width (float): Width of the element in pixels
        height (float): Height of the element in pixels
        angle (float): Rotation angle in radians (default: 0.0)
        stroke_color (str): Color of the element's border (default: "#000000")
        background_color (str): Fill color of the element (default: "transparent")
        fill_style (str): Fill pattern style (default: "hachure")
        stroke_width (int): Width of the border in pixels (default: 1)
        stroke_style (str): Style of the border line (default: "solid")
        roughness (int): Roughness level for hand-drawn appearance (default: 1)
        opacity (int): Opacity percentage 0-100 (default: 100)
        group_ids (List[str]): List of group IDs this element belongs to
        frame_id (Optional[str]): ID of the frame containing this element
        index (str): Z-index for layering (default: "a0")
        rounded_radius (Optional[int]): Corner radius for rounded rectangles
        bound_elements (List[Dict[str, Any]]): List of elements bound to this one
        updated (int): Timestamp of last update (default: 1)
        link (Optional[str]): URL link associated with the element
        locked (bool): Whether the element is locked from editing (default: False)
    """
    id: str
    type: str
    x: float
    y: float
    width: float
    height: float
    angle: float = 0.0
    stroke_color: str = "#000000"
    background_color: str = "transparent"
    fill_style: str = "hachure"
    stroke_width: int = 1
    stroke_style: str = "solid"
    roughness: int = 1
    opacity: int = 100
    group_ids: List[str] = None
    frame_id: Optional[str] = None
    index: str = "a0"
    rounded_radius: Optional[int] = None
    bound_elements: List[Dict[str, Any]] = None
    updated: int = 1
    link: Optional[str] = None
    locked: bool = False

    def __post_init__(self):
        """Initialize default values for mutable fields."""
        if self.group_ids is None:
            self.group_ids = []
        if self.bound_elements is None:
            self.bound_elements = []


@dataclass
class RectangleElement(BaseElement):
    """Represents a rectangle element in Excalidraw."""
    
    def __post_init__(self):
        super().__post_init__()
        if self.type != "rectangle":
            self.type = "rectangle"


@dataclass  
class TextElement(BaseElement):
    """Represents a text element in Excalidraw."""
    text: str = ""
    font_size: int = 20
    font_family: int = 1
    text_align: str = "left"
    vertical_align: str = "top"
    container_id: Optional[str] = None
    original_text: str = ""
    line_height: float = 1.25

    def __post_init__(self):
        super().__post_init__()
        if self.type != "text":
            self.type = "text"
        if not self.original_text:
            self.original_text = self.text


@dataclass
class ArrowElement(BaseElement):
    """Represents an arrow element in Excalidraw."""
    points: List[Tuple[float, float]] = None
    last_committed_point: Optional[Tuple[float, float]] = None
    start_binding: Optional[ElementBinding] = None
    end_binding: Optional[ElementBinding] = None
    start_arrow_head: Optional[str] = None
    end_arrow_head: str = "arrow"

    def __post_init__(self):
        super().__post_init__()
        if self.type != "arrow":
            self.type = "arrow"
        if self.points is None:
            self.points = [(0, 0), (0, 0)]


@dataclass
class Component:
    """
    Represents a diagram component (shape with optional text label).
    
    A Component combines a shape element (like a rectangle) with its associated
    text label to represent a logical unit in the diagram. This abstraction
    makes it easier to work with labeled shapes as single entities.
    
    Attributes:
        shape (BaseElement): The shape element (rectangle, circle, etc.)
        label (Optional[TextElement]): Associated text element, if any
        position (Tuple[float, float]): Position (x, y) derived from shape
        size (Tuple[float, float]): Size (width, height) derived from shape
    
    Example:
        >>> component = Component(
        ...     shape=rectangle_element,
        ...     label=text_element,
        ...     position=(100, 200),
        ...     size=(150, 100)
        ... )
        >>> print(f"Component '{component.label.text}' at {component.position}")
    """
    shape: BaseElement
    label: Optional[TextElement] = None
    position: Tuple[float, float] = (0, 0)
    size: Tuple[float, float] = (0, 0)

    def __post_init__(self):
        """Calculate position and size from shape."""
        self.position = (self.shape.x, self.shape.y)
        self.size = (self.shape.width, self.shape.height)


@dataclass
class Connection:
    """
    Represents a connection between two components via an arrow.
    
    A Connection captures the relationship between two diagram components
    through an arrow element, including directional information that can
    be used for natural language description generation.
    
    Attributes:
        source_component (Component): The component where the arrow starts
        target_component (Component): The component where the arrow ends
        arrow (ArrowElement): The arrow element representing the connection
        direction (str): Directional description (e.g., "left-to-right", "top-to-bottom")
    
    Example:
        >>> connection = Connection(
        ...     source_component=start_component,
        ...     target_component=end_component,
        ...     arrow=arrow_element,
        ...     direction="left-to-right"
        ... )
        >>> print(f"Connection from {connection.source_component.label.text} "
        ...       f"to {connection.target_component.label.text}")
    """
    source_component: Component
    target_component: Component
    arrow: ArrowElement
    direction: str = "left-to-right"


@dataclass
class DiagramStructure:
    """
    Represents the complete structure of a parsed diagram.
    
    This is the top-level data structure that organizes all diagram elements
    into logical categories for easier processing and description generation.
    It provides a hierarchical view of the diagram's content.
    
    Attributes:
        components (List[Component]): List of diagram components (labeled shapes)
        connections (List[Connection]): List of arrow connections between components
        standalone_elements (List[BaseElement]): List of unconnected elements
    
    Example:
        >>> structure = DiagramStructure(
        ...     components=[component1, component2],
        ...     connections=[connection1],
        ...     standalone_elements=[text_element]
        ... )
        >>> print(f"Diagram has {len(structure.components)} components, "
        ...       f"{len(structure.connections)} connections, "
        ...       f"{len(structure.standalone_elements)} standalone elements")
    """
    components: List[Component] = None
    connections: List[Connection] = None
    standalone_elements: List[BaseElement] = None

    def __post_init__(self):
        """Initialize default values for mutable fields."""
        if self.components is None:
            self.components = []
        if self.connections is None:
            self.connections = []
        if self.standalone_elements is None:
            self.standalone_elements = []



