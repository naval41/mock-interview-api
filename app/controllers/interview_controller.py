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
                    candidate_interview_id=mock_interview_id,
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