"""
Data models for design diagram parsing.
"""

from typing import Dict, List, Optional
from enum import Enum


class DiagramType(Enum):
    """Supported diagram types."""
    FLOWCHART = "flowchart"
    SEQUENCE = "sequence"
    CLASS = "class"
    ER = "er"
    STATE = "state"
    COMPONENT = "component"
    DEPLOYMENT = "deployment"
    USE_CASE = "use_case"
    ACTIVITY = "activity"
    WIREFRAME = "wireframe"
    MOCKUP = "mockup"
    ARCHITECTURE = "architecture"
    UNKNOWN = "unknown"


class DiagramElement:
    """Represents an element in a design diagram."""
    
    def __init__(
        self,
        element_type: str,
        name: str,
        properties: Optional[Dict] = None,
        connections: Optional[List[str]] = None
    ):
        self.element_type = element_type
        self.name = name
        self.properties = properties or {}
        self.connections = connections or []
    
    def to_dict(self) -> Dict:
        """Convert element to dictionary."""
        return {
            "element_type": self.element_type,
            "name": self.name,
            "properties": self.properties,
            "connections": self.connections
        }
    
    def __repr__(self) -> str:
        return f"DiagramElement(type={self.element_type}, name={self.name})"

