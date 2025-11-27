"""
Pipecat service for managing WebRTC connections and interview sessions.
"""

import asyncio
import base64
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import structlog

# Core pipecat imports (these should be available)
from pipecat.transports.smallwebrtc.connection import SmallWebRTCConnection

from cryptography.fernet import Fernet

from app.core.config import settings
from app.sao.daily_sao import daily_sao
from app.services.session_details_service import session_details_service

logger = structlog.get_logger()


class PipecatInterviewService:
    """
    Service for managing pipecat-based interview sessions.
    """
    
    def __init__(self):
        self.connections: Dict[str, SmallWebRTCConnection] = {}
        self.bot_instances: Dict[str, Any] = {}
        self.ice_servers = ["stun:stun.l.google.com:19302"]
        
    async def create_connection(self, room_id: str, sdp: str, sdp_type: str) -> Dict[str, Any]:
        """
        Create a new WebRTC connection for an interview session.
        
        Args:
            room_id: Unique identifier for the interview room
            sdp: WebRTC SDP offer
            sdp_type: Type of SDP (offer/answer)
            
        Returns:
            Dictionary containing connection details and SDP answer
        """
        try:
            # Check if connection already exists
            if room_id in self.connections:
                logger.info(f"Reusing existing connection for room_id: {room_id}")
                connection = self.connections[room_id]
                await connection.renegotiate(sdp=sdp, type=sdp_type, restart_pc=False)
            else:
                # Create new connection
                logger.info(f"Creating new connection for room_id: {room_id}")
                connection = SmallWebRTCConnection(self.ice_servers)
                await connection.initialize(sdp=sdp, type=sdp_type)
                
                # Store room_id in connection for reference (best-effort, ignored by type checker)
                setattr(connection, "room_id", room_id)  # type: ignore[attr-defined]
                
                # Setup connection event handlers
                await self._setup_connection_handlers(connection, room_id)
                
                # Store the connection
                self.connections[room_id] = connection
            
            # Get SDP answer
            answer = connection.get_answer()
            if answer is None:
                raise RuntimeError(f"SmallWebRTCConnection.get_answer() returned None for room_id {room_id}")
            
            # Update connection map with pc_id
            self.connections[answer["pc_id"]] = connection
            
            logger.info(f"Connection established for room_id: {room_id}, pc_id: {answer['pc_id']}")
            return answer
            
        except Exception as e:
            logger.error(f"Failed to create connection for room_id {room_id}: {e}")
            raise

    async def create_interview_room(self, room_id: str, user_id: str) -> Dict[str, Any]:
        """
        Create a Daily.co room and meeting token, returning encrypted credentials.
        """
        logger.info("Creating Daily room", room_id=room_id, user_id=user_id)

        if not settings.daily_api_key:
            raise RuntimeError("Daily API key is not configured")

        if not settings.encryption_key:
            raise RuntimeError("Encryption key is not configured")

        if not settings.daily_room_domain:
            raise RuntimeError("Daily room domain is not configured")

        existing_session = await session_details_service.get_by_candidate_interview_id(room_id)

        if existing_session and existing_session.roomUrl and existing_session.roomToken:
            logger.info(
                "Using existing session details",
                room_id=room_id,
            )
            room_url = existing_session.roomUrl
            token_value = existing_session.roomToken
        else:
            logger.info(
                "Creating a new Session Details",
                room_id=room_id,
            )
            expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

            room_response = await daily_sao.create_room(
                room_name=room_id,
                expires_at=expires_at,
            )
            room_url = room_response.get("url") or self._build_room_url(room_id)

            token_response = await daily_sao.create_meeting_token(
                room_name=room_id,
                user_id=user_id,
                expires_at=expires_at,
            )

            token_value = token_response.get("token")
            if not token_value:
                raise RuntimeError("Daily meeting token response did not include a token")

            await session_details_service.create_or_update_session(
                candidate_interview_id=room_id,
                generated_session_id=room_id,
                room_url=room_url,
                room_token=token_value,
            )

        #encrypted_url = self._encrypt_value(room_url)
        #encrypted_token = self._encrypt_value(token_value)

        logger.info("Daily room created successfully", room_id=room_id)

        return {
            "dailyRoom": room_url,
            "dailyToken": token_value,
            "sessionId": room_id
        }

    def _encrypt_value(self, value: str) -> str:
        fernet = self._get_fernet()
        return fernet.encrypt(value.encode("utf-8")).decode("utf-8")

    def decrypt_value(self, value: str) -> str:
        fernet = self._get_fernet()
        return fernet.decrypt(value.encode("utf-8")).decode("utf-8")

    def _get_fernet(self) -> Fernet:
        key = settings.encryption_key
        fernet_key = self._derive_fernet_key(key)
        return Fernet(fernet_key)

    @staticmethod
    def _derive_fernet_key(raw_key: str) -> bytes:
        raw_bytes = raw_key.encode("utf-8")

        try:
            decoded = base64.urlsafe_b64decode(raw_bytes)
            if len(decoded) == 32:
                return base64.urlsafe_b64encode(decoded)
        except Exception:
            pass

        digest = hashlib.sha256(raw_bytes).digest()
        return base64.urlsafe_b64encode(digest)

    def _build_room_url(self, room_id: str) -> str:
        base_domain = settings.daily_room_domain.rstrip("/")
        return f"{base_domain}/{room_id}"
    
    async def start_interview_session(
        self,
        room_id: str,
        token: str,
        user_id: str,
        interview_context: Optional[Any] = None,
        room_url: Optional[str] = None,
    ) -> bool:
        """
        Start an interview session using Daily.co transport with decrypted credentials.
        
        Args:
            room_id: Room identifier (candidate_interview_id)
            token: Daily meeting token
            user_id: User identifier
            interview_context: Interview context object with planner details
            room_url: Daily room URL
            
        Returns:
            True if session started successfully, False otherwise
        """
        logger.info(f"Starting interview session for room_id: {room_id}")
        
        if not room_url or not token:
            logger.error(f"Missing required credentials for room_id: {room_id}")
            return False
        
        if interview_context:
            logger.info(f"Interview context provided", 
                       mock_interview_id=interview_context.mock_interview_id,
                       planner_fields_count=len(interview_context.planner_fields))
        
        try:
            # Check if bot already exists for this room
            if room_id in self.bot_instances:
                bot_info = self.bot_instances[room_id]
                if bot_info.get("status") == "running":
                    logger.warning(f"Interview session already running for room_id: {room_id}")
                    return True
            
            # Import the InterviewBot class
            from app.interview_playground.interview_bot import InterviewBot
            
            # Create the interview bot instance with Daily transport credentials
            # Pass None for webrtc_connection since we're using Daily transport
            logger.info(f"Creating InterviewBot for room_id: {room_id} with Daily transport")
            bot = InterviewBot(
                webrtc_connection=None,
                room_id=room_id,
                interview_context=interview_context,
                room_url=room_url,
                room_joining_token=token
            )
            
            # Initialize the bot (this sets up Daily transport)
            logger.info(f"Initializing InterviewBot for room_id: {room_id}")
            await bot.initialize()
            
            # Start the bot in the background
            logger.info(f"Starting MockInterviewBot pipeline for room_id: {room_id}")
            bot_task = asyncio.create_task(bot.run())
            
            # Store the bot instance and task
            self.bot_instances[room_id] = {
                "bot": bot,
                "task": bot_task,
                "status": "running",
                "room_id": room_id,
                "started_at": asyncio.get_event_loop().time()
            }
            
            logger.info(f"✅ Interview session started successfully for room_id: {room_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start interview session for room_id {room_id}: {e}", exc_info=True)
            return False

    async def _setup_connection_handlers(self, connection: SmallWebRTCConnection, room_id: str):
        """Setup event handlers for the WebRTC connection."""
        
        @connection.event_handler("closed")
        async def handle_disconnected(webrtc_connection: SmallWebRTCConnection):
            logger.info(f"Connection closed event triggered for room_id: {room_id}")
            # Note: Cleanup is handled by explicit close_connection() call
            # This handler is just for logging unexpected disconnections
    
    async def start_interview_bot(self, room_id: str, interview_context: Optional[Any] = None) -> bool:
        """
        Start the interview bot for a specific room.
        
        Args:
            room_id: Room identifier
            interview_context: Optional interview context object with planner details
            
        Returns:
            True if bot started successfully, False otherwise
        """
        logger.info(f"Starting interview bot for room_id: {room_id}")
        
        if interview_context:
            logger.info(f"Interview context provided", 
                       mock_interview_id=interview_context.mock_interview_id,
                       planner_fields_count=len(interview_context.planner_fields))
        
        try:
            if room_id not in self.connections:
                logger.error(f"No connection found for room_id: {room_id}")
                return False
            
            connection = self.connections[room_id]
            
            # Import the InterviewBot class
            from app.interview_playground.interview_bot import InterviewBot
            
            # Create the interview bot instance with interview context
            logger.info(f"Creating InterviewBot for room_id: {room_id}")
            bot = InterviewBot(connection, room_id=room_id, interview_context=interview_context)
            
            # Start the bot
            logger.info(f"Starting InterviewBot for room_id: {room_id}")
            success = await bot.initialize()
                        # Start the bot in the background
            logger.info(f"Starting MockInterviewBot pipeline for room_id: {room_id}")
            bot_task = asyncio.create_task(bot.run())
            
            # Store the bot instance and task
            self.bot_instances[room_id] = {
                "bot": bot,
                "task": bot_task,
                "status": "running",
                "room_id": room_id,
                "started_at": asyncio.get_event_loop().time()
            }
            
            logger.info(f"✅ Interview bot started successfully for room_id: {room_id}")
            return True
            
        except Exception as e:
            print(f"Failed to start interview bot for room_id {room_id}: {e}")
            logger.error(f"Failed to start interview bot for room_id {room_id}: {e}")
            return False
    
    
    
    def get_connection_status(self, room_id: str) -> Dict[str, Any]:
        """Get the status of a connection."""
        if room_id not in self.connections:
            return {"status": "not_found"}
        
        connection = self.connections[room_id]
        bot_info = self.bot_instances.get(room_id, {})
        
        return {
            "status": "active",
            "room_id": room_id,
            "pc_id": getattr(connection, 'pc_id', 'unknown'),
            "has_bot": room_id in self.bot_instances,
            "bot_status": bot_info.get("status", "not_started"),
            "bot_started_at": bot_info.get("started_at")
        }
    
    def get_all_connections(self) -> Dict[str, Any]:
        """Get status of all active connections."""
        return {
            "total_connections": len(self.connections),
            "total_bots": len(self.bot_instances),
            "active_bots": len([b for b in self.bot_instances.values() if b.get("status") == "running"]),
            "connections": {
                room_id: self.get_connection_status(room_id)
                for room_id in self.connections.keys()
            }
        }
    
    async def close_connection(self, room_id: str) -> bool:
        """Close a specific connection and clean up all resources."""
        try:
            logger.info(f"In Service for close connection : {room_id}")
            
            # Check if bot instance exists
            if room_id not in self.bot_instances:
                logger.info(f"Connection not found for room_id: {room_id}")
                return False
            
            # Get bot instance and task BEFORE removing from bot_instances
            bot_info = self.bot_instances[room_id]
            bot = bot_info.get("bot")
            bot_task = bot_info.get("task")
            
            # STEP 1: Stop the bot properly (this stops the timer and cleans up)
            if bot:
                try:
                    logger.info(f"Stopping bot for room_id: {room_id}")
                    await bot.stop()  # This will stop the timer via timer_monitor.stop_current_timer()
                    logger.info(f"Bot stopped successfully for room_id: {room_id}")
                except Exception as e:
                    logger.error(f"Error stopping bot for room_id {room_id}: {e}")
                    # Continue with cleanup even if stop() fails
            
            # STEP 2: Cancel the bot task if it's still running
            if bot_task and not bot_task.done():
                logger.info(f"Cancelling bot task for room_id: {room_id}")
                bot_task.cancel()
                try:
                    await bot_task
                except asyncio.CancelledError:
                    logger.info(f"Bot task cancelled successfully for room_id: {room_id}")
            
            # STEP 3: Clean up bot instance
            self.bot_instances.pop(room_id, None)
            logger.info(f"Bot instance cleaned up for room_id: {room_id}")
            
            logger.info(f"✅ All resources cleaned up successfully for room_id: {room_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to close connection for room_id {room_id}: {str(e)}")
            return False
    
    async def cleanup_all(self):
        """Clean up all connections and bot instances."""
        try:
            for room_id in list(self.connections.keys()):
                await self.close_connection(room_id)
            logger.info("All connections cleaned up")
        except Exception as e:
            logger.error(f"Failed to cleanup connections: {e}")

    

    def get_answer(self, room_id: str) -> Dict[str, Any]:
        """
        Get the SDP answer for a connection.
        
        Args:
            room_id: Room identifier
            
        Returns:
            SDP answer with sdp, type, and pc_id
        """
        try:
            if room_id not in self.connections:
                return {"error": "Connection not found"}
            
            connection = self.connections[room_id]
            if hasattr(connection, 'get_answer'):
                answer = connection.get_answer()
                if answer is None:
                    raise RuntimeError(f"SmallWebRTCConnection.get_answer() returned None for room_id {room_id}")
                return answer
            else:
                # Fallback for placeholder connections
                return {
                    "sdp": "placeholder_sdp_answer",
                    "type": "answer", 
                    "pc_id": getattr(connection, "pc_id", f"pc_{room_id}")
                }
                
        except Exception as e:
            logger.error(f"Failed to get answer for room_id {room_id}: {e}")
            return {"error": str(e)}

    def get_bot_instance(self, room_id: str):
        """
        Get the bot instance for a specific room.
        
        Args:
            room_id: Room identifier
            
        Returns:
            Bot instance or None if not found
        """
        try:
            if room_id not in self.bot_instances:
                return None
            
            bot_info = self.bot_instances[room_id]
            if bot_info.get("status") == "running" and "bot" in bot_info:
                return bot_info["bot"]
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get bot instance for room_id {room_id}: {e}")
            return None

    def get_bot_status(self, room_id: str) -> Dict[str, Any]:
        """
        Get detailed status of the interview bot for a specific room.
        
        Args:
            room_id: Room identifier
            
        Returns:
            Detailed bot status information
        """
        try:
            if room_id not in self.bot_instances:
                return {"status": "not_found", "error": "Bot not found for this room"}
            
            bot_info = self.bot_instances[room_id]
            
            if bot_info.get("status") == "running" and "bot" in bot_info:
                # Get detailed status from the actual bot instance
                bot_instance = bot_info["bot"]
                if hasattr(bot_instance, 'get_status'):
                    bot_status = bot_instance.get_status()
                else:
                    bot_status = {"phase": "unknown", "is_running": True}
                
                return {
                    "status": "running",
                    "room_id": room_id,
                    "started_at": bot_info.get("started_at"),
                    "bot_details": bot_status,
                    "task_running": not bot_info.get("task", {}).done() if bot_info.get("task") else False
                }
            else:
                return {
                    "status": bot_info.get("status", "unknown"),
                    "room_id": room_id,
                    "error": "Bot not running or not properly initialized"
                }
                
        except Exception as e:
            logger.error(f"Failed to get bot status for room_id {room_id}: {e}")
            return {"status": "error", "error": str(e)}


# Global instance of the pipecat service
pipecat_service = PipecatInterviewService()
