"""
Pydantic schemas for interview-related API endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List


class WebRTCOffer(BaseModel):
    """Schema for WebRTC offer request."""
    room_id: str = Field(..., description="Unique identifier for the interview room")
    sdp: str = Field(..., description="WebRTC SDP offer")
    type: str = Field(..., description="Type of SDP (offer/answer)")
    restart_pc: Optional[bool] = Field(False, description="Whether to restart peer connection")


class WebRTCAnswer(BaseModel):
    """Schema for WebRTC answer response."""
    sdp: str = Field(..., description="WebRTC SDP answer")
    type: str = Field(..., description="Type of SDP (answer)")
    pc_id: str = Field(..., description="Peer connection identifier")


class StartInterviewRequest(BaseModel):
    """Schema for starting an interview session."""
    room_id: str = Field(..., description="Unique identifier for the interview room")
    interview_type: Optional[str] = Field("technical", description="Type of interview")
    duration_minutes: Optional[int] = Field(60, description="Interview duration in minutes")
    difficulty: Optional[str] = Field("medium", description="Interview difficulty level")
    topics: Optional[List[str]] = Field([], description="Interview topics to focus on")


class StartInterviewResponse(BaseModel):
    """Schema for interview start response."""
    success: bool = Field(..., description="Whether interview started successfully")
    message: str = Field(..., description="Response message")
    room_id: str = Field(..., description="Interview room identifier")
    session_id: Optional[str] = Field(None, description="Interview session identifier")
    connection_status: Optional[Dict[str, Any]] = Field(None, description="WebRTC connection status")


class InjectProblemRequest(BaseModel):
    """Schema for injecting a problem into the interview."""
    room_id: str = Field(..., description="Interview room identifier")
    problem_text: str = Field(..., description="Problem description to inject")
    problem_type: Optional[str] = Field("coding", description="Type of problem")
    difficulty: Optional[str] = Field("medium", description="Problem difficulty")


class InjectProblemResponse(BaseModel):
    """Schema for problem injection response."""
    success: bool = Field(..., description="Whether problem was injected successfully")
    message: str = Field(..., description="Response message")
    problem_id: Optional[str] = Field(None, description="Generated problem identifier")


class InjectCustomContextRequest(BaseModel):
    """Schema for injecting custom context into the interview."""
    room_id: str = Field(..., description="Interview room identifier")
    context_text: str = Field(..., description="Custom context to inject")
    context_type: Optional[str] = Field("general", description="Type of context")


class InjectCustomContextResponse(BaseModel):
    """Schema for custom context injection response."""
    success: bool = Field(..., description="Whether context was injected successfully")
    message: str = Field(..., description="Response message")


class InterviewStatusResponse(BaseModel):
    """Schema for interview status response."""
    room_id: str = Field(..., description="Interview room identifier")
    status: str = Field(..., description="Interview status")
    phase: str = Field(..., description="Current interview phase (waiting, instructions, problem_presentation, coding, solution_review)")
    is_running: bool = Field(..., description="Whether interview is currently running")
    phase_elapsed: Optional[int] = Field(None, description="Time elapsed in current phase (seconds)")
    phase_duration: Optional[int] = Field(None, description="Total duration of current phase (seconds)")
    current_question: Optional[str] = Field(None, description="Current question being asked")
    connection_info: Optional[Dict[str, Any]] = Field(None, description="WebRTC connection information")
    bot_status: Optional[Dict[str, Any]] = Field(None, description="Bot component status")


class ConnectionStatusResponse(BaseModel):
    """Schema for connection status response."""
    total_connections: int = Field(..., description="Total number of active connections")
    total_bots: int = Field(..., description="Total number of active bots")
    connections: Dict[str, Dict[str, Any]] = Field(..., description="Status of individual connections")


class InterviewSessionInfo(BaseModel):
    """Schema for interview session information."""
    session_id: str = Field(..., description="Unique session identifier")
    room_id: str = Field(..., description="Room identifier")
    user_id: str = Field(..., description="User identifier")
    interview_type: str = Field(..., description="Type of interview")
    status: str = Field(..., description="Session status")
    created_at: str = Field(..., description="Session creation timestamp")
    started_at: Optional[str] = Field(None, description="Session start timestamp")
    completed_at: Optional[str] = Field(None, description="Session completion timestamp")
    duration_minutes: int = Field(..., description="Planned duration in minutes")
    difficulty: str = Field(..., description="Interview difficulty")
    topics: List[str] = Field(..., description="Interview topics")


class InterviewErrorResponse(BaseModel):
    """Schema for interview error responses."""
    success: bool = Field(False, description="Always false for errors")
    error: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Error code for client handling")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
