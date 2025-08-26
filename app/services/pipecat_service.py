"""
Pipecat service for managing WebRTC connections and interview sessions.
"""

import asyncio
import os
from typing import Dict, Optional, Any
from contextlib import asynccontextmanager
import structlog

# Core pipecat imports (these should be available)
from pipecat.transports.network.webrtc_connection import SmallWebRTCConnection

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
                
                # Store room_id in connection for reference
                connection.room_id = room_id
                
                # Setup connection event handlers
                await self._setup_connection_handlers(connection, room_id)
                
                # Store the connection
                self.connections[room_id] = connection
            
            # Get SDP answer
            answer = connection.get_answer()
            
            # Update connection map with pc_id
            self.connections[answer["pc_id"]] = connection
            
            logger.info(f"Connection established for room_id: {room_id}, pc_id: {answer['pc_id']}")
            return answer
            
        except Exception as e:
            logger.error(f"Failed to create connection for room_id {room_id}: {e}")
            raise
    
    async def _setup_connection_handlers(self, connection: SmallWebRTCConnection, room_id: str):
        """Setup event handlers for the WebRTC connection."""
        
        @connection.event_handler("closed")
        async def handle_disconnected(webrtc_connection: SmallWebRTCConnection):
            logger.info(f"Connection closed for room_id: {room_id}")
            # Clean up connection and bot instance
            self.connections.pop(room_id, None)
            self.bot_instances.pop(room_id, None)
    
    async def start_interview_bot(self, room_id: str) -> bool:
        """
        Start the interview bot for a specific room.
        
        Args:
            room_id: Room identifier
            
        Returns:
            True if bot started successfully, False otherwise
        """
        logger.info(f"Starting interview bot for room_id: {room_id}")
        
        try:
            if room_id not in self.connections:
                logger.error(f"No connection found for room_id: {room_id}")
                return False
            
            connection = self.connections[room_id]
            
            # Import the InterviewBot class
            from app.interview_playground.interview_bot import InterviewBot
            
            # Create the interview bot instance
            logger.info(f"Creating InterviewBot for room_id: {room_id}")
            bot = InterviewBot(connection,room_id=room_id)
            
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
    
    async def inject_problem(self, room_id: str, problem_context: str) -> Dict[str, Any]:
        """
        Inject a problem context into the interview session.
        
        Args:
            room_id: Room identifier
            problem_context: Problem description to inject
            
        Returns:
            Success status and message
        """
        try:
            if room_id not in self.bot_instances:
                return {"success": False, "error": "Bot instance not found for this room"}
            
            # For now, just log the problem injection
            logger.info(f"Problem context would be injected for room_id: {room_id}: {problem_context[:50]}...")
            
            return {"success": True, "message": "Problem context injected successfully (placeholder)"}
            
        except Exception as e:
            logger.error(f"Failed to inject problem for room_id {room_id}: {e}")
            return {"success": False, "error": str(e)}
    
    async def inject_custom_context(self, room_id: str, context_text: str) -> Dict[str, Any]:
        """
        Inject custom context into the interview session.
        
        Args:
            room_id: Room identifier
            context_text: Custom context to inject
            
        Returns:
            Success status and message
        """
        try:
            if room_id not in self.bot_instances:
                return {"success": False, "error": "Bot instance not found for this room"}
            
            # For now, just log the context injection
            logger.info(f"Custom context would be injected for room_id: {room_id}: {context_text[:50]}...")
            
            return {"success": True, "message": "Custom context injected successfully (placeholder)"}
            
        except Exception as e:
            logger.error(f"Failed to inject custom context for room_id {room_id}: {e}")
            return {"success": False, "error": str(e)}
    
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
        """Close a specific connection."""
        try:
            if room_id in self.connections:
                connection = self.connections[room_id]
                await connection.close()
                self.connections.pop(room_id, None)
                self.bot_instances.pop(room_id, None)
                logger.info(f"Connection closed for room_id: {room_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to close connection for room_id {room_id}: {e}")
            return False
    
    async def cleanup_all(self):
        """Clean up all connections and bot instances."""
        try:
            for room_id in list(self.connections.keys()):
                await self.close_connection(room_id)
            logger.info("All connections cleaned up")
        except Exception as e:
            logger.error(f"Failed to cleanup connections: {e}")

    async def update_interview_phase(self, room_id: str, phase: str) -> bool:
        """
        Update the current phase of an interview session.
        
        Args:
            room_id: Room identifier
            phase: New phase (waiting, instructions, problem_presentation, coding, solution_review)
            
        Returns:
            Success status
        """
        try:
            if room_id not in self.bot_instances:
                return False
            
            bot_instance = self.bot_instances[room_id]["bot"]
            # Update phase in bot instance
            if hasattr(bot_instance, 'update_phase'):
                await bot_instance.update_phase(phase)
            else:
                # For now, just log the phase update
                logger.info(f"Phase update not supported in simple InterviewBot: {phase}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update phase for room_id {room_id}: {e}")
            return False

    async def start_interview_timer(self, room_id: str) -> bool:
        """
        Start the interview timer for a specific room.
        
        Args:
            room_id: Room identifier
            
        Returns:
            Success status
        """
        try:
            if room_id not in self.bot_instances:
                return False
            
            bot_instance = self.bot_instances[room_id]["bot"]
            # Start timer in bot instance
            if hasattr(bot_instance, 'start_timer'):
                await bot_instance.start_timer()
            else:
                # For now, just log the timer start
                logger.info(f"Timer started for room_id: {room_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start timer for room_id {room_id}: {e}")
            return False

    async def pause_interview_timer(self, room_id: str) -> bool:
        """
        Pause the interview timer for a specific room.
        
        Args:
            room_id: Room identifier
            
        Returns:
            Success status
        """
        try:
            if room_id not in self.bot_instances:
                return False
            
            bot_instance = self.bot_instances[room_id]["bot"]
            # Pause timer in bot instance
            if hasattr(bot_instance, 'pause_timer'):
                await bot_instance.pause_timer()
            else:
                # For now, just log the timer pause
                logger.info(f"Timer paused for room_id: {room_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to pause timer for room_id {room_id}: {e}")
            return False

    async def reset_interview_timer(self, room_id: str) -> bool:
        """
        Reset the interview timer for a specific room.
        
        Args:
            room_id: Room identifier
            
        Returns:
            Success status
        """
        try:
            if room_id not in self.bot_instances:
                return False
            
            bot_instance = self.bot_instances[room_id]["bot"]
            # Reset timer in bot instance
            if hasattr(bot_instance, 'reset_timer'):
                await bot_instance.reset_timer()
            else:
                # For now, just log the timer reset
                logger.info(f"Timer reset for room_id: {room_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to reset timer for room_id {room_id}: {e}")
            return False

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
                return connection.get_answer()
            else:
                # Fallback for placeholder connections
                return {
                    "sdp": "placeholder_sdp_answer",
                    "type": "answer", 
                    "pc_id": connection.get("pc_id", f"pc_{room_id}")
                }
                
        except Exception as e:
            logger.error(f"Failed to get answer for room_id {room_id}: {e}")
            return {"error": str(e)}

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
