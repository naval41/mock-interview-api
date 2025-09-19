"""
Entities package for the mock interview API.
Contains business logic entities that represent core domain concepts.
"""

from .interview_context import InterviewContext
from .task_event import TaskEvent, TaskProperties

__all__ = ["InterviewContext", "TaskEvent", "TaskProperties"]
