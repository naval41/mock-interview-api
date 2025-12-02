"""
Interview controller with pipecat integration for real-time voice interviews.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from app.core.security import validate_request
from app.services.pipecat_service import pipecat_service
from app.services.interview_context_service import interview_context_service
from app.services.session_details_service import session_details_service
from app.services.candidate_interview_service import candidate_interview_service
import structlog
from datetime import datetime

logger = structlog.get_logger()

router = APIRouter(tags=["Interview"])


class CreateRoomRequest(BaseModel):
    candidate_interview_id: str
    user_id: str

class CreateRoomResponse(BaseModel):
    dailyRoom: str
    dailyToken: str
    sessionId: str


class StartInterviewSessionRequest(BaseModel):
    candidateInterviewId: str
    user_id: str


class StartInterviewSessionResponse(BaseModel):
    success: bool
    room_id: str


async def validate_interview_access(room_id: str, user_id: str) -> None:
    """
    Common validation method to verify interview access.
    Validates that room_id and user_id are provided, and that the interview
    exists and belongs to the authenticated user.
    
    Args:
        room_id: The candidate interview ID (room ID)
        user_id: The authenticated user ID
        
    Raises:
        HTTPException: If validation fails (400 for missing params, 403 for access denied)
    """
    if not room_id or not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="room_id and user_id are required",
        )
    
    # Validate that the interview exists and belongs to the user
    try:
        await candidate_interview_service.validate_interview_ownership(room_id, user_id)
    except ValueError as e:
        logger.warning("Interview ownership validation failed", 
                     room_id=room_id, 
                     user_id=user_id, 
                     error=str(e))
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.post("/create-room", response_model=CreateRoomResponse)
async def create_room(payload: CreateRoomRequest, user: dict = Depends(validate_request)):
    """
    Create a new interview room and return encrypted credentials.

    The encryption logic is delegated to the pipecat service, which will be
    implemented separately.
    """
    try:
        room_id = payload.candidate_interview_id.strip()
        user_id = user.get("user_id")

        logger.info("Creating room", room_id=room_id, user_id=user_id)

        # Validate interview access (checks required params and ownership)
        await validate_interview_access(room_id, user_id)

        result = await pipecat_service.create_interview_room(
            room_id=room_id,
            user_id=user_id,
        )

        if not result or "dailyRoom" not in result or "dailyToken" not in result:
            raise RuntimeError("Failed to generate room credentials")

        await start_interview(room_id, user_id)

        return CreateRoomResponse(**result)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to create room", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create interview room",
        )

async def start_interview(candidate_interview_id: str, user_id: str):
    
    if not candidate_interview_id or not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="room_id and user_id are required",
        )

    try:
        session_details = await session_details_service.get_by_candidate_interview_id(candidate_interview_id)

        if not session_details or not session_details.roomUrl or not session_details.roomToken:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session details not found for room_id",
            )

        interview_context = await interview_context_service.build_interview_context(
            candidate_interview_id=candidate_interview_id,
            user_id=user_id,
            session_id=candidate_interview_id,
        )

        started = await pipecat_service.start_interview_session(
            room_id=candidate_interview_id,
            token=session_details.roomToken,
            user_id=user_id,
            interview_context=interview_context,
            room_url=session_details.roomUrl,
        )
        return StartInterviewSessionResponse(success=started, room_id=candidate_interview_id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to start interview session", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to start interview session",
        )

@router.delete("/close-connection/{room_id}")
async def close_connection(
    room_id: str,
    user: dict = Depends(validate_request)
):
    """
    Close a specific interview connection.
    """
    try:
        logger.info(f"Closing connection for room {room_id}")

        user_id = user.get("user_id")
        
        # Validate interview access (checks required params and ownership)
        await validate_interview_access(room_id, user_id)
        
        # Close the connection
        success = await pipecat_service.close_connection(room_id)
        
        logger.info(f"Closing success : {success}")
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

@router.get("/interview/{room_id}/events")
async def interview_events_stream(room_id: str):
    """Server-Sent Events stream for interview phase changes and updates."""
    from fastapi.responses import StreamingResponse
    import asyncio
    import json
    
    async def event_generator():
        """Generate SSE events for interview updates."""
        try:
            # Check if interview bot exists
            bot_instance = pipecat_service.get_bot_instance(room_id)
            if not bot_instance:
                yield f"event: error\ndata: {json.dumps({'message': 'Interview bot not found'})}\n\n"
                return
            
            # Send initial connection event
            yield f"event: connected\ndata: {json.dumps({'room_id': room_id, 'timestamp': datetime.utcnow().isoformat()})}\n\n"
            
            # Register this SSE connection with the bot
            if not hasattr(bot_instance, 'sse_connections'):
                bot_instance.sse_connections = set()
            
            # Create a queue for this SSE connection
            event_queue = asyncio.Queue()
            bot_instance.sse_connections.add(event_queue)
            
            try:
                # Send periodic heartbeat and listen for events
                while True:
                    try:
                        # Wait for events with timeout for heartbeat
                        event_data = await asyncio.wait_for(event_queue.get(), timeout=30.0)
                        
                        # Log the received event data for debugging
                        logger.debug("Received SSE event data", 
                                   room_id=room_id, 
                                   event_keys=list(event_data.keys()) if isinstance(event_data, dict) else "not_dict",
                                   event_data_type=type(event_data).__name__)
                        
                        # Handle different event data formats
                        if isinstance(event_data, dict):
                            # Check for 'type' or 'event_type' field
                            event_type = event_data.get('type') or event_data.get('event_type')
                            event_payload = event_data.get('data', {})
                            
                            if event_type:
                                yield f"event: {event_type}\ndata: {json.dumps(event_payload)}\n\n"
                                logger.debug("Sent SSE event", 
                                           room_id=room_id, 
                                           event_type=event_type,
                                           payload_size=len(json.dumps(event_payload)))
                            else:
                                logger.error("SSE event data missing type field", 
                                           room_id=room_id, 
                                           available_keys=list(event_data.keys()))
                                # Send as generic event
                                yield f"event: data\ndata: {json.dumps(event_data)}\n\n"
                        else:
                            logger.error("SSE event data is not a dictionary", 
                                       room_id=room_id, 
                                       event_data_type=type(event_data).__name__,
                                       event_data=str(event_data))
                            # Send as string event
                            yield f"event: raw\ndata: {json.dumps({'raw_data': str(event_data)})}\n\n"
                            
                    except asyncio.TimeoutError:
                        # Send heartbeat every 30 seconds
                        heartbeat_data = {
                            'timestamp': datetime.utcnow().isoformat(),
                            'room_id': room_id
                        }
                        yield f"event: heartbeat\ndata: {json.dumps(heartbeat_data)}\n\n"
                        
            except asyncio.CancelledError:
                logger.info("SSE connection cancelled", room_id=room_id)
            finally:
                # Clean up connection
                if hasattr(bot_instance, 'sse_connections'):
                    bot_instance.sse_connections.discard(event_queue)
                    
        except Exception as e:
            logger.error("Error in SSE event generator", room_id=room_id, error=str(e))
            error_data = {'message': f'Server error: {str(e)}'}
            yield f"event: error\ndata: {json.dumps(error_data)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )