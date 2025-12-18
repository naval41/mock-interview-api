"""
TaskEvent entity for SSE data structure sent from Timer Class to frontend.
This entity represents the structured data sent via Server-Sent Events during interview sessions.
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from app.models.enums import WorkflowStepType, ToolName


@dataclass
class TaskProperties:
    """
    Properties specific to the task being sent.
    Contains task-specific data like question ID and other relevant properties.
    """
    question_id: Optional[str] = None
    # Additional properties can be added here as needed
    # e.g., time_limit: Optional[int] = None
    # e.g., difficulty_level: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert TaskProperties to dictionary representation"""
        result = {}
        if self.question_id is not None:
            result["questionId"] = self.question_id
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskProperties':
        """Create TaskProperties instance from dictionary"""
        return cls(
            question_id=data.get("questionId")
        )


@dataclass
class TaskEvent:
    """
    Entity representing the structured data sent via SSE events from Timer Class to frontend.
    
    This entity contains:
    - taskType: The type of workflow task (from WorkflowStepType enum)
    - toolName: List of tools available for this task (from ToolName enum)
    - task_definition: Optional text containing question or problem statement
    - task_properties: Task-specific properties including question ID
    - tool_properties: Tool-specific properties as raw JSON (pass-through from database)
    """
    
    task_type: WorkflowStepType
    tool_name: List[ToolName]
    task_definition: Optional[str] = None
    task_properties: Optional[TaskProperties] = None
    tool_properties: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Validate and set default values after initialization"""
        if not isinstance(self.task_type, WorkflowStepType):
            raise ValueError("task_type must be a WorkflowStepType enum value")
        
        if not isinstance(self.tool_name, list):
            raise ValueError("tool_name must be a list")
        
        if self.tool_name:
            for tool in self.tool_name:
                if not isinstance(tool, ToolName):
                    raise ValueError("All tools in tool_name must be ToolName enum values")
        
        # Initialize task_properties if not provided
        if self.task_properties is None:
            self.task_properties = TaskProperties()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the TaskEvent to a dictionary representation for SSE data"""
        return {
            "taskType": self.task_type.value,
            "toolName": [tool.value for tool in self.tool_name],
            "task_definition": self.task_definition,
            "task_properties": self.task_properties.to_dict() if self.task_properties else {},
            "tool_properties": self.tool_properties if self.tool_properties else {}
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskEvent':
        """Create a TaskEvent instance from a dictionary"""
        # Convert task_type from string to enum
        task_type = WorkflowStepType(data["taskType"])
        
        # Convert tool_name from list of strings to list of enums
        tool_name = [ToolName(tool) for tool in data.get("toolName", [])]
        
        # Handle task_properties
        task_properties = None
        if "task_properties" in data and data["task_properties"]:
            task_properties = TaskProperties.from_dict(data["task_properties"])
        
        # Handle tool_properties - pass through as dict (no parsing needed)
        tool_properties = None
        if "tool_properties" in data and isinstance(data.get("tool_properties"), dict):
            tool_properties = data["tool_properties"]
        
        return cls(
            task_type=task_type,
            tool_name=tool_name,
            task_definition=data.get("task_definition"),
            task_properties=task_properties,
            tool_properties=tool_properties
        )
    
    def add_tool(self, tool: ToolName) -> None:
        """Add a tool to the tool_name list"""
        if not isinstance(tool, ToolName):
            raise ValueError("tool must be a ToolName enum value")
        
        if tool not in self.tool_name:
            self.tool_name.append(tool)
    
    def remove_tool(self, tool: ToolName) -> None:
        """Remove a tool from the tool_name list"""
        if tool in self.tool_name:
            self.tool_name.remove(tool)
    
    def set_question_id(self, question_id: str) -> None:
        """Set the question ID in task_properties"""
        if self.task_properties is None:
            self.task_properties = TaskProperties()
        self.task_properties.question_id = question_id
    
    def __str__(self) -> str:
        """String representation of the TaskEvent"""
        return (f"TaskEvent(task_type={self.task_type.value}, "
                f"tool_name={[tool.value for tool in self.tool_name]}, "
                f"task_definition={self.task_definition})")
    
    def __repr__(self) -> str:
        """Detailed representation of the TaskEvent"""
        return (f"TaskEvent(task_type={self.task_type.value}, "
                f"tool_name={[tool.value for tool in self.tool_name]}, "
                f"task_definition='{self.task_definition}', "
                f"task_properties={self.task_properties}, "
                f"tool_properties={self.tool_properties})")
