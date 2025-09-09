"""
Interview controller with pipecat integration for real-time voice interviews.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_async_session
from app.core.security import validate_request
from app.services.pipecat_service import pipecat_service
from app.services.interview_context_service import interview_context_service
from app.schemas.interview_schemas import (
    WebRTCOffer, WebRTCAnswer, StartInterviewRequest, StartInterviewResponse,
    InjectProblemRequest, InjectProblemResponse, InjectCustomContextRequest,
    InjectCustomContextResponse, InterviewStatusResponse, ConnectionStatusResponse
)
import structlog
import uuid
from datetime import datetime

logger = structlog.get_logger()

router = APIRouter(prefix="/api", tags=["Interview"])


@router.get("/test")
async def test_endpoint():
    """Simple test endpoint to debug hanging issues."""
    print("Test endpoint called")
    logger.info("Test endpoint called")
    return {"message": "Test endpoint working", "timestamp": datetime.utcnow().isoformat()}


@router.post("/start-interview", response_model=StartInterviewResponse)
async def start_interview(
    request: StartInterviewRequest,
    background_tasks: BackgroundTasks = None
):
    """
    Start a new interview session with pipecat integration.
    """
    try:
        room_id = request.room_id
        
        print(f"Starting interview in room {room_id}")
        logger.info(f"Starting interview in room {room_id}")
        
        # Create a unique session ID
        session_id = str(uuid.uuid4())
        
        # Store interview session info (you can extend this with database storage)
        session_info = {
            "session_id": session_id,
            "room_id": room_id,
            "interview_type": request.interview_type,
            "status": "created",
            "created_at": datetime.utcnow().isoformat(),
            "duration_minutes": request.duration_minutes,
            "difficulty": request.difficulty,
            "topics": request.topics
        }
        
        # Start the interview bot in background (if WebRTC connection exists)
        if background_tasks:
            background_tasks.add_task(
                pipecat_service.start_interview_bot, 
                room_id
            )
        
        logger.info(f"Interview session {session_id} created for room {room_id}")
        
        return StartInterviewResponse(
            success=True,
            message="Interview session created successfully",
            room_id=room_id,
            session_id=session_id,
            connection_status=pipecat_service.get_connection_status(room_id)
        )
        
    except Exception as e:
        logger.error(f"Failed to start interview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start interview"
        )

@router.post("/offer")
async def handle_webrtc_offer(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Handle WebRTC offer and establish connection for interview.
    This is the equivalent of the /api/offer endpoint from the reference implementation.
    """
    try:
        logger.info(f"Received offer request: {request}")
        
        query_params = request.query_params
        room_id = query_params.get("room_id")
        user_id = query_params.get("user_id")
        mock_interview_id = query_params.get("mock_interview_id")
        
        # Extract body parameters
        body = await request.json()

        
        logger.info(f"Processing WebRTC offer for room {room_id}, user {user_id}, mock_interview_id {mock_interview_id}")

        # Build interview context if this is a new connection
        interview_context = None
        if not (room_id and room_id in pipecat_service.connections):
            try:
                # Create interview context from mock_interview_id and user_id
                interview_context = await interview_context_service.build_interview_context(
                    mock_interview_id=mock_interview_id,
                    user_id=user_id,
                    session_id=room_id  # Use room_id as session_id
                )
                logger.info(f"Built interview context for room {room_id}", 
                           context_summary=interview_context.get_context_summary())
            except ValueError as e:
                logger.error(f"Failed to build interview context: {e}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid interview setup: {str(e)}"
                )
            except Exception as e:
                logger.error(f"Unexpected error building interview context: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to initialize interview context"
                )

        # Check if connection already exists for this room
        if room_id and room_id in pipecat_service.connections:
            pipecat_connection = pipecat_service.connections[room_id]
            logger.info(f"Reusing existing connection for room_id: {room_id}")
            
            # Renegotiate existing connection
            await pipecat_service.renegotiate_connection(
                room_id=room_id,
                sdp=body["sdp"], 
                sdp_type=body["type"], 
                restart_pc=body.get("restart_pc", False)
            )
        else:
            # Create new WebRTC connection
            answer = await pipecat_service.create_connection(
                room_id=room_id,
                sdp=body["sdp"],
                sdp_type=body["type"]
            )
            
            # Start the interview bot in background with interview context
            background_tasks.add_task(
                pipecat_service.start_interview_bot, 
                room_id,
                interview_context  # Pass the interview context to the bot
            )
            
            logger.info(f"New WebRTC connection established for room {room_id}")
            
            return answer
        
        # For existing connections, get the current answer
        answer = pipecat_service.get_answer(room_id)
        
        logger.info(f"WebRTC connection handled for room {room_id}")
        return answer
        
    except Exception as e:
        logger.error(f"Failed to handle WebRTC offer: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to establish WebRTC connection"
        )


@router.post("/inject-problem", response_model=InjectProblemResponse)
async def inject_problem(
    request: InjectProblemRequest,
    user=Depends(validate_request)
):
    """
    Inject a problem context into the interview session.
    """
    try:
        user_id = user.get("user_id")
        room_id = request.room_id
        
        logger.info(f"Injecting problem for user {user_id} in room {room_id}")
        
        # Inject the problem into the interview bot
        result = await pipecat_service.inject_problem(
            room_id=room_id,
            problem_context=request.problem_text
        )
        
        if result["success"]:
            return InjectProblemResponse(
                success=True,
                message=result["message"],
                problem_id=str(uuid.uuid4())  # Generate a unique problem ID
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to inject problem: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to inject problem"
        )


@router.post("/inject-custom-context", response_model=InjectCustomContextResponse)
async def inject_custom_context(
    request: InjectCustomContextRequest,
    user=Depends(validate_request)
):
    """
    Inject custom context into the interview session.
    """
    try:
        user_id = user.get("user_id")
        room_id = request.room_id
        
        logger.info(f"Injecting custom context for user {user_id} in room {room_id}")
        
        # Inject the custom context into the interview bot
        result = await pipecat_service.inject_custom_context(
            room_id=room_id,
            context_text=request.context_text
        )
        
        if result["success"]:
            return InjectCustomContextResponse(
                success=True,
                message=result["message"]
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to inject custom context: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to inject custom context"
        )


@router.get("/status/{room_id}", response_model=InterviewStatusResponse)
async def get_interview_status(
    room_id: str
):
    """
    Get the current status of an interview session.
    """
    try:
        logger.info(f"Getting interview status for room {room_id}")
        
        # Get connection status
        connection_status = pipecat_service.get_connection_status(room_id)
        
        # Get bot status if available
        bot_status = pipecat_service.get_bot_status(room_id)
        
        return InterviewStatusResponse(
            room_id=room_id,
            status=connection_status.get("status", "not_found"),
            phase=bot_status.get("phase", "waiting") if bot_status else "waiting",
            is_running=connection_status.get("status") == "active",
            phase_elapsed=bot_status.get("phase_elapsed") if bot_status else None,
            phase_duration=bot_status.get("phase_duration") if bot_status else None,
            current_question=bot_status.get("current_question") if bot_status else None,
            connection_info=connection_status,
            bot_status=bot_status
        )
        
    except Exception as e:
        logger.error(f"Failed to get interview status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get interview status"
        )


@router.get("/connections/status", response_model=ConnectionStatusResponse)
async def get_all_connections():
    """
    Get status of all active connections (admin endpoint).
    """
    try:
        logger.info(f"Getting connection status for all connections")
        
        # Get all connection statuses
        status_info = pipecat_service.get_all_connections()
        
        return ConnectionStatusResponse(**status_info)
        
    except Exception as e:
        logger.error(f"Failed to get connection status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get connection status"
        )


@router.delete("/close-connection/{room_id}")
async def close_connection(
    room_id: str
):
    """
    Close a specific interview connection.
    """
    try:
        logger.info(f"Closing connection for room {room_id}")
        
        # Close the connection
        success = await pipecat_service.close_connection(room_id)
        
        if success:
            return {"success": True, "message": f"Connection closed for room {room_id}"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connection not found for room {room_id}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to close connection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to close connection"
        )


@router.put("/interview/{room_id}/phase")
async def update_interview_phase(
    room_id: str,
    phase: str,
    background_tasks: BackgroundTasks = None
):
    """
    Update the current phase of an interview session.
    Phases: waiting, instructions, problem_presentation, coding, solution_review
    """
    try:
        logger.info(f"Updating interview phase to {phase} for room {room_id}")
        
        # Validate phase
        valid_phases = ["waiting", "instructions", "problem_presentation", "coding", "solution_review"]
        if phase not in valid_phases:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid phase. Must be one of: {', '.join(valid_phases)}"
            )
        
        # Update phase in pipecat service
        success = await pipecat_service.update_interview_phase(room_id, phase)
        
        if success:
            return {
                "success": True,
                "message": f"Interview phase updated to {phase}",
                "room_id": room_id,
                "phase": phase
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Interview session not found for room {room_id}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update interview phase: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update interview phase"
        )


@router.post("/interview/{room_id}/timer/start")
async def start_interview_timer(room_id: str):
    """Start the interview timer for a specific room."""
    try:
        logger.info(f"Starting interview timer for room {room_id}")
        
        success = await pipecat_service.start_interview_timer(room_id)
        
        if success:
            return {
                "success": True,
                "message": "Interview timer started",
                "room_id": room_id
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Interview session not found for room {room_id}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start interview timer: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start interview timer"
        )


@router.post("/interview/{room_id}/timer/pause")
async def pause_interview_timer(room_id: str):
    """Pause the interview timer for a specific room."""
    try:
        logger.info(f"Pausing interview timer for room {room_id}")
        
        success = await pipecat_service.pause_interview_timer(room_id)
        
        if success:
            return {
                "success": True,
                "message": "Interview timer paused",
                "room_id": room_id
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Interview session not found for room {room_id}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to pause interview timer: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to pause interview timer"
        )


@router.post("/interview/{room_id}/timer/reset")
async def reset_interview_timer(room_id: str):
    """Reset the interview timer for a specific room."""
    try:
        logger.info(f"Resetting interview timer for room {room_id}")
        
        success = await pipecat_service.reset_interview_timer(room_id)
        
        if success:
            return {
                "success": True,
                "message": "Interview timer reset",
                "room_id": room_id
            }
        else:
                    raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Interview session not found for room {room_id}"
        )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reset interview timer: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset interview timer"
        )
