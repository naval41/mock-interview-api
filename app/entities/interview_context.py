"""
InterviewContext entity for tracking interview session state and context.
This entity represents the current state of an ongoing interview session.
"""

from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime


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
    
    def get_session_duration(self) -> int:
        """Get the total duration of the session in seconds"""
        current_time = datetime.utcnow()
        duration = (current_time - self.started_at).total_seconds()
        return int(duration)
    
    def get_context_summary(self) -> dict:
        """Get a summary of the current interview context"""
        return {
            "mock_interview_id": self.mock_interview_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "interview_planner_id": self.interview_planner_id,
            "current_workflow_step_sequence": self.current_workflow_step_sequence,
            "current_question_id": self.current_question_id,
            "current_workflow_step_id": self.current_workflow_step_id,
            "started_at": self.started_at.isoformat(),
            "session_duration_seconds": self.get_session_duration()
        }
    
    def reset_context(self) -> None:
        """Reset the interview context to initial state"""
        self.current_workflow_step_sequence = 0
        self.current_question_id = None
        self.current_workflow_step_id = None
    
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
            "current_workflow_step_id": self.current_workflow_step_id
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'InterviewContext':
        """Create an InterviewContext instance from a dictionary"""
        # Handle datetime fields
        if 'started_at' in data and isinstance(data['started_at'], str):
            data['started_at'] = datetime.fromisoformat(data['started_at'])
        
        return cls(**data)
    
    def __str__(self) -> str:
        """String representation of the InterviewContext"""
        return (f"InterviewContext(mock_interview_id='{self.mock_interview_id}', "
                f"user_id='{self.user_id}', session_id='{self.session_id}', "
                f"interview_planner_id='{self.interview_planner_id}', "
                f"sequence={self.current_workflow_step_sequence})")
    
    def __repr__(self) -> str:
        """Detailed representation of the InterviewContext"""
        return (f"InterviewContext(mock_interview_id='{self.mock_interview_id}', "
                f"user_id='{self.user_id}', session_id='{self.session_id}', "
                f"interview_planner_id='{self.interview_planner_id}', "
                f"current_workflow_step_sequence={self.current_workflow_step_sequence}, "
                f"started_at={self.started_at}, "
                f"current_question_id={self.current_question_id}, "
                f"current_workflow_step_id={self.current_workflow_step_id})")
