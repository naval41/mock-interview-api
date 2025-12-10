"""
ToolProperties entity for tool-specific configuration data.
This entity represents tool-specific JSON data stored in CandidateInterviewPlanner.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ToolProperties:
    """
    Properties specific to tools used in interview planner steps.
    Contains tool-specific configuration like programming languages.
    """
    languages: Optional[List[str]] = None
    
    def __post_init__(self):
        """Validate and set default values after initialization"""
        if self.languages is None:
            self.languages = []
        
        # Validate that languages is a list of strings
        if not isinstance(self.languages, list):
            raise ValueError("languages must be a list")
        
        for lang in self.languages:
            if not isinstance(lang, str):
                raise ValueError("All languages must be strings")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert ToolProperties to dictionary representation"""
        result = {}
        if self.languages is not None and len(self.languages) > 0:
            result["languages"] = self.languages
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ToolProperties':
        """Create ToolProperties instance from dictionary"""
        languages = data.get("languages")
        
        # Handle None or empty cases
        if languages is None:
            languages = []
        elif not isinstance(languages, list):
            raise ValueError("languages must be a list")
        
        return cls(languages=languages)
    
    def __str__(self) -> str:
        """String representation of the ToolProperties"""
        return f"ToolProperties(languages={self.languages})"
    
    def __repr__(self) -> str:
        """Detailed representation of the ToolProperties"""
        return f"ToolProperties(languages={self.languages})"

