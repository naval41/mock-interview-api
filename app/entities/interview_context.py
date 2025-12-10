"""
InterviewContext entity for tracking interview session state and context.
This entity represents the current state of an ongoing interview session.
"""

from typing import Optional, List
from dataclasses import dataclass, field
from datetime import datetime, time
from app.models.enums import ToolName, WorkflowStepType, QuestionType
from app.entities.tool_properties import ToolProperties


def parse_tool_names_from_string(tool_string: Optional[str]) -> List[ToolName]:
    """
    Parse comma-separated tool names from database string into List[ToolName].
    
    Args:
        tool_string: Comma-separated string of tool names from database (e.g., "CODE_EDITOR,BASE")
        
    Returns:
        List of ToolName enums
    """
    if not tool_string:
        return []
    
    tool_names = []
    for tool_str in tool_string.split(','):
        tool_str = tool_str.strip()
        if tool_str:
            try:
                tool_names.append(ToolName(tool_str))
            except ValueError:
                # If tool name is not valid, skip it
                continue
    
    return tool_names


def format_tool_names_to_string(tool_names: List[ToolName]) -> str:
    """
    Convert List[ToolName] to comma-separated string for database storage.
    
    Args:
        tool_names: List of ToolName enums
        
    Returns:
        Comma-separated string (e.g., "CODE_EDITOR,BASE")
    """
    if not tool_names:
        return ""
    
    return ",".join([tool.value for tool in tool_names])


@dataclass
class PlannerField:
    """
    Field object representing a single planner entry with key details.
    This holds the essential information from CandidateInterviewPlanner table.
    """
    question_id: str
    knowledge_bank_id: str
    interview_instructions: Optional[str]
    duration: int  # Duration in minutes
    question_text: Optional[str] = None  # Question text from InterviewQuestion table
    tool_name: Optional[List[ToolName]] = None  # List of tools required for this planner step
    tool_properties: Optional[ToolProperties] = None  # Tool-specific properties (e.g., languages)
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    sequence: int = 0
    
    def __post_init__(self):
        """Validate required fields after initialization"""
        if self.sequence < 0:
            raise ValueError("sequence cannot be negative")
        if self.duration <= 0:
            raise ValueError("duration must be positive (in minutes)")
        
        # Initialize tool_name as empty list if not provided
        if self.tool_name is None:
            self.tool_name = []
        
        # Validate tool_name list
        if self.tool_name:
            for tool in self.tool_name:
                if not isinstance(tool, ToolName):
                    raise ValueError("All tools in tool_name must be ToolName enum values")
    
    def to_dict(self) -> dict:
        """Convert the planner field to a dictionary representation"""
        return {
            "question_id": self.question_id,
            "knowledge_bank_id": self.knowledge_bank_id,
            "interview_instructions": self.interview_instructions,
            "duration": self.duration,
            "question_text": self.question_text,
            "tool_name": [tool.value for tool in self.tool_name] if self.tool_name else [],
            "tool_properties": self.tool_properties.to_dict() if self.tool_properties else {},
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "sequence": self.sequence
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'PlannerField':
        """Create a PlannerField instance from a dictionary"""
        # Handle time fields
        if 'start_time' in data and data['start_time'] and isinstance(data['start_time'], str):
            data['start_time'] = datetime.fromisoformat(data['start_time']).time()
        if 'end_time' in data and data['end_time'] and isinstance(data['end_time'], str):
            data['end_time'] = datetime.fromisoformat(data['end_time']).time()
        
        # Handle tool_name field - convert from list of strings to list of ToolName enums
        if 'tool_name' in data and isinstance(data['tool_name'], list):
            data['tool_name'] = [ToolName(tool) for tool in data['tool_name']]
        elif 'tool_name' not in data:
            data['tool_name'] = []
        
        # Handle tool_properties field - convert from dict to ToolProperties
        if 'tool_properties' in data and data['tool_properties']:
            if isinstance(data['tool_properties'], dict):
                data['tool_properties'] = ToolProperties.from_dict(data['tool_properties'])
            else:
                data['tool_properties'] = None
        elif 'tool_properties' not in data:
            data['tool_properties'] = None
        
        return cls(**data)
    
    def __str__(self) -> str:
        """String representation of the PlannerField"""
        return (f"PlannerField(question_id='{self.question_id}', "
                f"knowledge_bank_id='{self.knowledge_bank_id}', "
                f"sequence={self.sequence})")
    
    def set_question_text(self, question_text: str) -> None:
        """Set the question text for this planner field"""
        self.question_text = question_text
    
    def add_tool(self, tool: ToolName) -> None:
        """Add a tool to the tool_name list"""
        if not isinstance(tool, ToolName):
            raise ValueError("tool must be a ToolName enum value")
        
        if self.tool_name is None:
            self.tool_name = []
        
        if tool not in self.tool_name:
            self.tool_name.append(tool)
    
    def remove_tool(self, tool: ToolName) -> None:
        """Remove a tool from the tool_name list"""
        if self.tool_name is not None and tool in self.tool_name:
            self.tool_name.remove(tool)
    
    def set_tools(self, tools: List[ToolName]) -> None:
        """Set the complete list of tools for this planner field"""
        if not isinstance(tools, list):
            raise ValueError("tools must be a list")
        
        for tool in tools:
            if not isinstance(tool, ToolName):
                raise ValueError("All tools must be ToolName enum values")
        
        self.tool_name = tools.copy()
    
    def set_tools_from_string(self, tool_string: Optional[str]) -> None:
        """Set tools from comma-separated database string"""
        self.tool_name = parse_tool_names_from_string(tool_string)
    
    def get_tools_as_string(self) -> str:
        """Get tools as comma-separated string for database storage"""
        return format_tool_names_to_string(self.tool_name or [])
    
    def __repr__(self) -> str:
        """Detailed representation of the PlannerField"""
        tool_names = [tool.value for tool in self.tool_name] if self.tool_name else []
        return (f"PlannerField(question_id='{self.question_id}', "
                f"knowledge_bank_id='{self.knowledge_bank_id}', "
                f"interview_instructions='{self.interview_instructions}', "
                f"question_text='{self.question_text}', "
                f"tool_name={tool_names}, "
                f"tool_properties={self.tool_properties}, "
                f"start_time={self.start_time}, end_time={self.end_time}, "
                f"sequence={self.sequence})")


@dataclass
class InterviewContext:
    """
    Entity representing the context of an ongoing interview session.
    
    This entity tracks:
    - Interview identification (mock_interview_id, candidate_interview_id, user_id, session_id, interview_planner_id)
    - Current workflow step sequence
    - Session timing (started_at)
    - Current question and workflow step
    """
    
    # Core identifiers
    mock_interview_id: str
    user_id: str
    session_id: str
    interview_planner_id: str
    candidate_interview_id: Optional[str] = None  # ID from CandidateInterview table for transcript storage
    
    # Current workflow step sequence
    current_workflow_step_sequence: int = 0  # Default starting sequence
    
    # Session timing
    started_at: datetime = field(default_factory=datetime.utcnow)
    
    # Current context
    current_question_id: Optional[str] = None
    current_question_text: Optional[str] = None  # Question text from InterviewQuestion table
    current_tool_name: Optional[List[ToolName]] = None  # Current tools for the active planner step
    current_workflow_step_id: Optional[str] = None
    
    def __post_init__(self):
        """Validate and set default values after initialization"""
        if not self.mock_interview_id:
            raise ValueError("mock_interview_id cannot be empty")
        if not self.user_id:
            raise ValueError("user_id cannot be empty")
        if not self.session_id:
            raise ValueError("session_id cannot be empty")
        if not self.interview_planner_id:
            raise ValueError("interview_planner_id cannot be empty")
        
        # Initialize current_tool_name as empty list if not provided
        if self.current_tool_name is None:
            self.current_tool_name = []
        
        # Validate current_tool_name list
        if self.current_tool_name:
            for tool in self.current_tool_name:
                if not isinstance(tool, ToolName):
                    raise ValueError("All tools in current_tool_name must be ToolName enum values")
    
    # Planner details (ordered by sequence)
    planner_fields: List[PlannerField] = field(default_factory=list)
    
    def update_workflow_step_sequence(self, sequence: int) -> None:
        """Update the current workflow step sequence"""
        if sequence < 0:
            raise ValueError("Sequence cannot be negative")
        self.current_workflow_step_sequence = sequence
    
    def update_question_context(self, question_id: str, question_text: Optional[str] = None, 
                               tool_name: Optional[List[ToolName]] = None, workflow_step_id: Optional[str] = None) -> None:
        """Update the current question context"""
        self.current_question_id = question_id
        self.current_question_text = question_text
        if tool_name is not None:
            self.current_tool_name = tool_name.copy()
        if workflow_step_id:
            self.current_workflow_step_id = workflow_step_id
    
    def update_workflow_step(self, workflow_step_id: str) -> None:
        """Update the current workflow step"""
        self.current_workflow_step_id = workflow_step_id
    
    def move_to_next_sequence(self) -> None:
        """Move to the next sequence in the workflow"""
        self.current_workflow_step_sequence += 1
    
    def add_planner_field(self, planner_field: PlannerField) -> None:
        """Add a planner field to the context"""
        self.planner_fields.append(planner_field)
        # Keep planner fields sorted by sequence
        self.planner_fields.sort(key=lambda pf: pf.sequence)
    
    def get_current_planner_field(self) -> Optional[PlannerField]:
        """Get the current planner field based on sequence"""
        if not self.planner_fields:
            return None
        
        # Find planner field with matching sequence
        for planner_field in self.planner_fields:
            if planner_field.sequence == self.current_workflow_step_sequence:
                return planner_field
        
        # If no match found, log warning for debugging
        import structlog
        logger = structlog.get_logger()
        logger.warning("No planner field found for current sequence", 
                      current_sequence=self.current_workflow_step_sequence,
                      available_sequences=[pf.sequence for pf in self.planner_fields],
                      mock_interview_id=self.mock_interview_id)
        
        return None
    
    def get_next_planner_field(self) -> Optional[PlannerField]:
        """Get the next planner field in sequence"""
        if not self.planner_fields:
            return None
        
        next_sequence = self.current_workflow_step_sequence + 1
        for planner_field in self.planner_fields:
            if planner_field.sequence == next_sequence:
                return planner_field
        
        return None
    
    def get_planner_fields_by_sequence(self, start_sequence: int, end_sequence: Optional[int] = None) -> List[PlannerField]:
        """Get planner fields within a sequence range"""
        if not self.planner_fields:
            return []
        
        if end_sequence is None:
            return [pf for pf in self.planner_fields if pf.sequence >= start_sequence]
        
        return [pf for pf in self.planner_fields if start_sequence <= pf.sequence <= end_sequence]
    
    def update_current_question_from_planner(self) -> None:
        """Update current question context from the current planner field"""
        current_planner = self.get_current_planner_field()
        if current_planner:
            self.current_question_id = current_planner.question_id
            self.current_question_text = current_planner.question_text
            self.current_tool_name = current_planner.tool_name.copy() if current_planner.tool_name else []
    
    def get_current_question_text(self) -> Optional[str]:
        """Get the current question text, either from current context or current planner field"""
        if self.current_question_text:
            return self.current_question_text
        
        # Fallback to getting from current planner field
        current_planner = self.get_current_planner_field()
        if current_planner and current_planner.question_text:
            return current_planner.question_text
        
        return None
    
    def get_current_tool_names(self) -> List[ToolName]:
        """Get the current tool names, either from current context or current planner field"""
        if self.current_tool_name:
            return self.current_tool_name.copy()
        
        # Fallback to getting from current planner field
        current_planner = self.get_current_planner_field()
        if current_planner and current_planner.tool_name:
            return current_planner.tool_name.copy()
        
        return []
    
    def populate_question_texts(self, interview_questions: dict) -> None:
        """
        Populate question_text fields for all planner fields using a dictionary of InterviewQuestion objects.
        
        Args:
            interview_questions: Dictionary with question_id as key and InterviewQuestion object as value
        """
        for planner_field in self.planner_fields:
            if planner_field.question_id in interview_questions:
                question = interview_questions[planner_field.question_id]
                planner_field.question_text = question.question
        
        # Update current question text if current question is set
        if self.current_question_id and self.current_question_id in interview_questions:
            question = interview_questions[self.current_question_id]
            self.current_question_text = question.question
    
    def populate_tool_names_from_planners(self, planner_data: dict) -> None:
        """
        Populate tool_name fields for all planner fields from CandidateInterviewPlanner database data.
        
        Args:
            planner_data: Dictionary with question_id as key and CandidateInterviewPlanner object as value
        """
        for planner_field in self.planner_fields:
            if planner_field.question_id in planner_data:
                planner = planner_data[planner_field.question_id]
                # Set tools directly from database toolName field
                planner_field.set_tools_from_string(planner.toolName)
        
        # Update current tool names if current question is set
        if self.current_question_id and self.current_question_id in planner_data:
            planner = planner_data[self.current_question_id]
            self.current_tool_name = parse_tool_names_from_string(planner.toolName)
    
    def populate_all_data(self, interview_questions: dict, planner_data: Optional[dict] = None) -> None:
        """
        Populate both question texts and tool names for all planner fields.
        
        Args:
            interview_questions: Dictionary with question_id as key and InterviewQuestion object as value
            planner_data: Optional dictionary with question_id as key and CandidateInterviewPlanner object as value
        """
        # Populate question texts
        self.populate_question_texts(interview_questions)
        
        # Populate tool names from planner data if provided
        if planner_data:
            self.populate_tool_names_from_planners(planner_data)
    
    def get_session_duration(self) -> int:
        """Get the total duration of the session in seconds"""
        current_time = datetime.utcnow()
        duration = (current_time - self.started_at).total_seconds()
        return int(duration)
    
    def get_context_summary(self) -> dict:
        """Get a summary of the current interview context"""
        current_planner = self.get_current_planner_field()
        return {
            "mock_interview_id": self.mock_interview_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "interview_planner_id": self.interview_planner_id,
            "current_workflow_step_sequence": self.current_workflow_step_sequence,
            "current_question_id": self.current_question_id,
            "current_question_text": self.current_question_text,
            "current_tool_name": [tool.value for tool in self.current_tool_name] if self.current_tool_name else [],
            "current_workflow_step_id": self.current_workflow_step_id,
            "started_at": self.started_at.isoformat(),
            "session_duration_seconds": self.get_session_duration(),
            "planner_fields_count": len(self.planner_fields),
            "current_planner_field": current_planner.to_dict() if current_planner else None,
            "planner_fields": [pf.to_dict() for pf in self.planner_fields]
        }
    
    def reset_context(self) -> None:
        """Reset the interview context to initial state"""
        self.current_workflow_step_sequence = 0
        self.current_question_id = None
        self.current_question_text = None
        self.current_tool_name = []
        self.current_workflow_step_id = None
        # Note: planner_fields are kept as they represent the interview structure
    
    def to_dict(self) -> dict:
        """Convert the entity to a dictionary representation"""
        return {
            "mock_interview_id": self.mock_interview_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "interview_planner_id": self.interview_planner_id,
            "current_workflow_step_sequence": self.current_workflow_step_sequence,
            "started_at": self.started_at.isoformat(),
            "current_question_id": self.current_question_id,
            "current_question_text": self.current_question_text,
            "current_tool_name": [tool.value for tool in self.current_tool_name] if self.current_tool_name else [],
            "current_workflow_step_id": self.current_workflow_step_id,
            "planner_fields": [pf.to_dict() for pf in self.planner_fields]
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'InterviewContext':
        """Create an InterviewContext instance from a dictionary"""
        # Handle datetime fields
        if 'started_at' in data and isinstance(data['started_at'], str):
            data['started_at'] = datetime.fromisoformat(data['started_at'])
        
        # Handle current_tool_name field - convert from list of strings to list of ToolName enums
        if 'current_tool_name' in data and isinstance(data['current_tool_name'], list):
            data['current_tool_name'] = [ToolName(tool) for tool in data['current_tool_name']]
        elif 'current_tool_name' not in data:
            data['current_tool_name'] = []
        
        # Handle planner fields
        if 'planner_fields' in data and isinstance(data['planner_fields'], list):
            data['planner_fields'] = [PlannerField.from_dict(pf) for pf in data['planner_fields']]
        else:
            data['planner_fields'] = []
        
        return cls(**data)
    
    def __str__(self) -> str:
        """String representation of the InterviewContext"""
        return (f"InterviewContext(mock_interview_id='{self.mock_interview_id}', "
                f"candidate_interview_id='{self.candidate_interview_id}', "
                f"user_id='{self.user_id}', session_id='{self.session_id}', "
                f"interview_planner_id='{self.interview_planner_id}', "
                f"sequence={self.current_workflow_step_sequence}, "
                f"planner_fields_count={len(self.planner_fields)})")
    
    def __repr__(self) -> str:
        """Detailed representation of the InterviewContext"""
        return (f"InterviewContext(mock_interview_id='{self.mock_interview_id}', "
                f"candidate_interview_id='{self.candidate_interview_id}', "
                f"user_id='{self.user_id}', session_id='{self.session_id}', "
                f"interview_planner_id='{self.interview_planner_id}', "
                f"current_workflow_step_sequence={self.current_workflow_step_sequence}, "
                f"started_at={self.started_at}, "
                f"current_question_id={self.current_question_id}, "
                f"current_workflow_step_id={self.current_workflow_step_id}, "
                f"planner_fields={len(self.planner_fields)} items)")
