"""
InterviewContext entity for tracking interview session state and context.
This entity represents the current state of an ongoing interview session.
"""

from typing import Optional, List
from dataclasses import dataclass, field
from datetime import datetime, time


@dataclass
class PlannerField:
    """
    Field object representing a single planner entry with key details.
    This holds the essential information from CandidateInterviewPlanner table.
    """
    question_id: str
    knowledge_bank_id: str
    interview_instructions: Optional[str]
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    sequence: int = 0
    
    def __post_init__(self):
        """Validate required fields after initialization"""
        if not self.question_id:
            raise ValueError("question_id cannot be empty")
        if not self.knowledge_bank_id:
            raise ValueError("knowledge_bank_id cannot be empty")
        if self.sequence < 0:
            raise ValueError("sequence cannot be negative")
    
    def to_dict(self) -> dict:
        """Convert the planner field to a dictionary representation"""
        return {
            "question_id": self.question_id,
            "knowledge_bank_id": self.knowledge_bank_id,
            "interview_instructions": self.interview_instructions,
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
        
        return cls(**data)
    
    def __str__(self) -> str:
        """String representation of the PlannerField"""
        return (f"PlannerField(question_id='{self.question_id}', "
                f"knowledge_bank_id='{self.knowledge_bank_id}', "
                f"sequence={self.sequence})")
    
    def __repr__(self) -> str:
        """Detailed representation of the PlannerField"""
        return (f"PlannerField(question_id='{self.question_id}', "
                f"knowledge_bank_id='{self.knowledge_bank_id}', "
                f"interview_instructions='{self.interview_instructions}', "
                f"start_time={self.start_time}, end_time={self.end_time}, "
                f"sequence={self.sequence})")


@dataclass
class InterviewContext:
    """
    Entity representing the context of an ongoing interview session.
    
    This entity tracks:
    - Interview identification (mock_interview_id, user_id, session_id, interview_planner_id)
    - Current workflow step sequence
    - Session timing (started_at)
    - Current question and workflow step
    """
    
    # Core identifiers
    mock_interview_id: str
    user_id: str
    session_id: str
    interview_planner_id: str
    
    # Current workflow step sequence
    current_workflow_step_sequence: int = 0  # Default starting sequence
    
    # Session timing
    started_at: datetime = field(default_factory=datetime.utcnow)
    
    # Current context
    current_question_id: Optional[str] = None
    current_workflow_step_id: Optional[str] = None
    
    # Planner details (ordered by sequence)
    planner_fields: List[PlannerField] = field(default_factory=list)
    
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
    
    def update_workflow_step_sequence(self, sequence: int) -> None:
        """Update the current workflow step sequence"""
        if sequence < 0:
            raise ValueError("Sequence cannot be negative")
        self.current_workflow_step_sequence = sequence
    
    def update_question_context(self, question_id: str, workflow_step_id: Optional[str] = None) -> None:
        """Update the current question context"""
        self.current_question_id = question_id
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
            "current_workflow_step_id": self.current_workflow_step_id,
            "started_at": self.started_at.isoformat(),
            "session_duration_seconds": self.get_session_duration(),
            "planner_fields_count": len(self.planner_fields),
            "current_planner_field": current_planner.to_dict() if current_planner else None
        }
    
    def reset_context(self) -> None:
        """Reset the interview context to initial state"""
        self.current_workflow_step_sequence = 0
        self.current_question_id = None
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
            "current_workflow_step_id": self.current_workflow_step_id,
            "planner_fields": [pf.to_dict() for pf in self.planner_fields]
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'InterviewContext':
        """Create an InterviewContext instance from a dictionary"""
        # Handle datetime fields
        if 'started_at' in data and isinstance(data['started_at'], str):
            data['started_at'] = datetime.fromisoformat(data['started_at'])
        
        # Handle planner fields
        if 'planner_fields' in data and isinstance(data['planner_fields'], list):
            data['planner_fields'] = [PlannerField.from_dict(pf) for pf in data['planner_fields']]
        else:
            data['planner_fields'] = []
        
        return cls(**data)
    
    def __str__(self) -> str:
        """String representation of the InterviewContext"""
        return (f"InterviewContext(mock_interview_id='{self.mock_interview_id}', "
                f"user_id='{self.user_id}', session_id='{self.session_id}', "
                f"interview_planner_id='{self.interview_planner_id}', "
                f"sequence={self.current_workflow_step_sequence}, "
                f"planner_fields_count={len(self.planner_fields)})")
    
    def __repr__(self) -> str:
        """Detailed representation of the InterviewContext"""
        return (f"InterviewContext(mock_interview_id='{self.mock_interview_id}', "
                f"user_id='{self.user_id}', session_id='{self.session_id}', "
                f"interview_planner_id='{self.interview_planner_id}', "
                f"current_workflow_step_sequence={self.current_workflow_step_sequence}, "
                f"started_at={self.started_at}, "
                f"current_question_id={self.current_question_id}, "
                f"current_workflow_step_id={self.current_workflow_step_id}, "
                f"planner_fields={len(self.planner_fields)} items)")
