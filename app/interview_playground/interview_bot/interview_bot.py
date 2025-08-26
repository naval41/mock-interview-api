"""
Mock Interview Bot that coordinates all pipecat components for interview sessions.
"""

import asyncio
import os
from typing import Optional, Any, Dict
from loguru import logger
from app.core.config import settings

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.frameworks.rtvi import RTVIConfig, RTVIObserver, RTVIProcessor
from pipecat.services.gemini_multimodal_live.gemini import GeminiMultimodalLiveLLMService, InputParams
from pipecat.services.google.llm import GoogleLLMService
from pipecat.transports.base_transport import TransportParams
from pipecat.transports.network.small_webrtc import SmallWebRTCTransport

from app.interview_playground.stt.stt_service import STTService
from app.interview_playground.tts.tts_service import TTSService


class InterviewBot:
    """Main orchestrator class for the mock interview bot."""
    
    def __init__(self, webrtc_connection, room_id: str = None):
        self.webrtc_connection = webrtc_connection
        self.room_id = room_id or getattr(webrtc_connection, 'pc_id', 'unknown')
        
        # Create a logger context for this session
        self.logger = logger.bind(room_id=self.room_id)
        
        # Pipecat components
        self.transport = None
        self.tts = None
        self.stt = None
        self.llm_service = None
        self.context_aggregator = None
        self.rtvi_processor = None
        self.pipeline = None
        self.task = None
        self.runner = None
        
        # Interview state
        self.is_running = False
        self.current_question = None
        self.interview_phase = "introduction"
        
        self.logger.info(f"🎯 Mock Interview Bot initialized for room_id: {self.room_id}")
        
    async def initialize(self):
        """Initialize all bot components."""
        try:
            # Initialize transport
            await self._setup_transport()
            
            # Initialize LLM service
            await self._setup_llm_service()
            
            # Initialize TTS service
            await self._setup_tts()
            
            # Initialize STT service
            await self._setup_stt()
            
            # Initialize context aggregator
            await self._setup_context_aggregator()
            
            # Initialize RTVI processor
            await self._setup_rtvi_processor()
            
            # Setup pipeline
            await self._setup_pipeline()
            
            # Setup event handlers
            await self._setup_event_handlers()
            
            self.logger.info("🎯 Mock Interview Bot initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize bot: {e}")
            raise
    
    async def _setup_transport(self):
        """Setup WebRTC transport."""
        try:
            # Try to setup VAD, but make it optional
            vad_analyzer = None
            try:
                vad_analyzer = SileroVADAnalyzer()
                self.logger.info("🎤 Silero VAD analyzer setup completed")
            except ImportError as e:
                self.logger.warning(f"Silero VAD not available: {e}. Continuing without VAD.")
            except Exception as e:
                self.logger.warning(f"Failed to setup VAD: {e}. Continuing without VAD.")
            
            transport_params = TransportParams(
                video_in_enabled=False,
                video_out_enabled=False,
                video_out_is_live=False,
                audio_in_enabled=True,
                audio_out_enabled=True,
                vad_analyzer=vad_analyzer,  # Can be None
            )
            
            self.transport = SmallWebRTCTransport(
                webrtc_connection=self.webrtc_connection,
                params=transport_params
            )
            
            self.logger.info("🔗 Transport setup completed")
            
        except Exception as e:
            self.logger.error(f"Failed to setup transport: {e}")
            raise
    
    async def _setup_llm_service(self):
        """Setup LLM service using Google API key."""
        try:
            google_key = settings.google_api_key
            if not google_key:
                raise ValueError("google_api_key not found in settings. Please check your config/local.env file")
            
            try:
                from app.interview_playground.llm.llm_service import LLMService
                llm_service = LLMService(provider="google", api_key=google_key, model="gemini-2.0-flash-001")
                self.llm_service = llm_service.setup_processor()
                self.logger.info("🤖 LLM service setup completed")
                return
            except ImportError as e:
                self.logger.error(f"LLM service not available: {e}. Please check your imports.")
                raise
            except Exception as e:
                self.logger.error(f"Failed to setup Google LLM: {e}")
                raise
            
        except Exception as e:
            self.logger.error(f"Failed to setup LLM service: {e}")
            raise
    
    async def _setup_tts(self):
        """Setup TTS service."""
        try:
            deepgram_key = settings.deepgram_api_key
            if not deepgram_key:
                raise ValueError("deepgram_api_key not found in settings. Please check your config/local.env file")
            
            ttsService = TTSService(provider="deepgram", api_key=deepgram_key)
            self.tts = ttsService.setup_processor()
            self.logger.info("🔊 TTS service setup completed")
            
        except Exception as e:
            self.logger.error(f"Failed to setup TTS service: {e}")
            raise
    
    async def _setup_stt(self):
        """Setup STT service."""
        try:
            deepgram_key = settings.deepgram_api_key
            if not deepgram_key:
                raise ValueError("deepgram_api_key not found in settings. Please check your config/local.env file")
            
            sttService = STTService(api_key=deepgram_key, provider="deepgram")

            self.stt = sttService.setup_processor()
            self.logger.info("🎤 STT service setup completed")
            
        except Exception as e:
            self.logger.error(f"Failed to setup STT service: {e}")
            raise
    
    async def _setup_context_aggregator(self):
        """Setup context aggregator for conversation memory."""
        try:
        
            context = OpenAILLMContext([
                {
                    "role": "user",
                    "content": "Start by greeting the user warmly and introducing yourself.",
                }
            ])
            
            self.context_aggregator = self.llm_service.create_context_aggregator(context)
            self.logger.info("📚 Context aggregator setup completed")
                
        except Exception as e:
            self.logger.error(f"Failed to setup context aggregator: {e}")
            raise
    
    async def _setup_rtvi_processor(self):
        """Setup RTVI processor for real-time voice interaction."""
        try:
            # RTVIConfig expects a config dict with the services
            self.rtvi_processor = RTVIProcessor(config=RTVIConfig(config=[]))
            
            #self.rtvi_processor = RTVIProcessor(rtvi_config)
            self.logger.info("🎙️ RTVI processor setup completed")
            
        except Exception as e:
            self.logger.error(f"Failed to setup RTVI processor: {e}")
            raise
    
    async def _setup_pipeline(self):
        """Setup the audio processing pipeline."""
        try:
            # For now, let's create a minimal pipeline without the transport
            # The transport will be handled separately by the WebRTC connection

            self.pipeline = Pipeline([
                self.transport.input(),
                self.stt,
                self.context_aggregator.user(),
                self.rtvi_processor,
                self.llm_service,
                self.tts,
                self.transport.output(),
                self.context_aggregator.assistant(),
            ])  
            
            # Create pipeline task
            self.task = PipelineTask(
                self.pipeline,
                params=PipelineParams(
                    allow_interruptions=True
                ),
                observers=[RTVIObserver(self.rtvi_processor)],
            )
            
            # Create pipeline runner
            self.runner = PipelineRunner()
            
            self.logger.info("🔧 Pipeline setup completed (without transport)")
            
        except Exception as e:
            self.logger.error(f"Failed to setup pipeline: {e}")
            raise
    
    async def _setup_event_handlers(self):
        """Setup event handlers for the pipeline."""
        try:
            # For now, let's skip the observer setup to avoid compatibility issues
            # The pipeline already has observers configured in the task
            self.logger.info("👁️ Event handlers setup completed (observers configured in pipeline)")
            
        except Exception as e:
            self.logger.error(f"Failed to setup event handlers: {e}")
            raise
    
    async def run(self):
        """Run the interview bot."""
        try:
            if not all([self.transport, self.rtvi_processor, self.pipeline, self.task, self.runner]):
                raise RuntimeError("Bot not properly initialized")
            
            self.is_running = True
            self.logger.info(f"🚀 Starting interview bot for room_id: {self.room_id}")
            
            # Start the pipeline
            await self.runner.run(self.task)
            
            self.logger.info(f"✅ Interview bot running for room_id: {self.room_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to run interview bot: {e}")
            self.is_running = False
            raise
    
    async def stop(self):
        """Stop the interview bot."""
        try:
            if self.runner:
                await self.runner.stop()
            
            if self.transport:
                await self.transport.close()
            
            self.is_running = False
            self.logger.info(f"🛑 Interview bot stopped for room_id: {self.room_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to stop interview bot: {e}")
    
    async def inject_problem_context(self, problem_text: str):
        """Inject a problem context into the LLM conversation."""
        try:
            if self.context_aggregator:
                # Add problem context to the conversation
                await self.context_aggregator.add_message(
                    role="system",
                    content=f"Interview Problem: {problem_text}"
                )
                self.logger.info(f"Problem context injected: {problem_text[:50]}...")
            
        except Exception as e:
            self.logger.error(f"Failed to inject problem context: {e}")
    
    async def inject_custom_context(self, context_text: str):
        """Inject custom context into the LLM conversation."""
        try:
            if self.context_aggregator:
                # Add custom context to the conversation
                await self.context_aggregator.add_message(
                    role="system",
                    content=f"Custom Context: {context_text}"
                )
                self.logger.info(f"Custom context injected: {context_text[:50]}...")
            
        except Exception as e:
            self.logger.error(f"Failed to inject custom context: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the bot."""
        return {
            "room_id": self.room_id,
            "is_running": self.is_running,
            "interview_phase": self.interview_phase,
            "current_question": self.current_question,
            "components": {
                "transport": self.transport is not None,
                "llm_service": self.llm_service is not None,
                "tts": self.tts is not None,
                "stt": self.stt is not None,
                "context_aggregator": self.context_aggregator is not None,
                "rtvi_processor": self.rtvi_processor is not None,
                "pipeline": self.pipeline is not None
            }
        }
