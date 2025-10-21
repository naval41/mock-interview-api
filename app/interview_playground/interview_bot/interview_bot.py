"""
Mock Interview Bot that coordinates all pipecat components for interview sessions.
"""

import asyncio
import os
from typing import Optional, Any, Dict
from pipecat.processors.aggregators.llm_response import LLMUserAggregatorParams
import structlog
from pipecat.audio.vad.vad_analyzer import VADParams
from app.core.config import settings

from pipecat.audio.interruptions.min_words_interruption_strategy import MinWordsInterruptionStrategy
from pipecat.audio.turn.smart_turn.base_smart_turn import SmartTurnParams
from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3
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

from app.interview_playground.processors.processors_service import ProcessorsService
from app.interview_playground.processors.context_switch_processor import ContextSwitchProcessor
from app.interview_playground.processors.interview_gate_processor import InterviewGateProcessor
from app.interview_playground.processors.interview_closure_handler import InterviewClosureHandler
from app.interview_playground.stt.stt_service import STTService
from app.interview_playground.transport.transport_service import TransportService
from app.interview_playground.tts.tts_service import TTSService
from app.interview_playground.timer.interview_timer_monitor import InterviewTimerMonitor
from app.interview_playground.transcript.transcript_service import TranscriptService


class InterviewBot:
    """Main orchestrator class for the mock interview bot."""
    
    def __init__(self, webrtc_connection, room_id: str = None, interview_context=None):
        self.webrtc_connection = webrtc_connection
        self.room_id = room_id or getattr(webrtc_connection, 'pc_id', 'unknown')
        self.interview_context = interview_context
        
        # Create a logger context for this session
        self.logger = structlog.get_logger().bind(room_id=self.room_id)
        
        # Log interview context if provided
        if self.interview_context:
            self.logger.info("Interview context loaded", 
                           mock_interview_id=self.interview_context.mock_interview_id,
                           planner_fields_count=len(self.interview_context.planner_fields),
                           current_sequence=self.interview_context.current_workflow_step_sequence)
        
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
        self.custom_processors = None
        
        # Timer and context management components
        self.context_switch_processor = None
        self.timer_monitor = None
        
        # Interview gate and closure handling components
        self.interview_gate_processor = None
        self.interview_closure_handler = None
        
        # Transcript processing
        self.transcript_service = TranscriptService()
        self.transcript_processor = None
        
        # Interview state management
        self.interview_phase = "initializing"
        self._final_message_sent = False

                # Processors service for context processing
        self.processors_service = ProcessorsService(
            code_context=True,  # CodeContextProcessor is enabled
            design_context=True,  # DesignContextProcessor is enabled
            max_code_snippets=10,
            max_design_elements=15
        )
        
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

            # Initialize Custom processor
            await self._setup_custom_processor()
            
            # Initialize Context Switch processor
            await self._setup_context_switch_processor()
            
            # Initialize Interview Gate processor
            await self._setup_interview_gate_processor()
            
            # Initialize Interview Closure handler
            await self._setup_interview_closure_handler()
            
            # Initialize Timer Monitor
            await self._setup_timer_monitor()
            
            # Initialize Transcript Processor
            await self._setup_transcript_processor()
            
            # Setup pipeline
            await self._setup_pipeline()
            
            # Setup event handlers
            await self._setup_event_handlers()
            
            # Start initial planner timer if interview context exists
            await self._start_initial_interview_phase()
            
            self.logger.info("🎯 Mock Interview Bot initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize bot: {e}")
            raise
    
    async def _setup_pipeline(self):
        """Setup the audio processing pipeline."""
        try:
            
            pipeline_componenets = await self._get_pipeline_components()
            
            self.pipeline = Pipeline(pipeline_componenets)  
            
            # Create pipeline task
            self.task = PipelineTask(
                self.pipeline,
                params=PipelineParams(
                    allow_interruptions=True,
                    interruption_strategies=[MinWordsInterruptionStrategy(min_words=3)],
                ),
                observers=[RTVIObserver(self.rtvi_processor)],
            )
            
            # Create pipeline runner
            self.runner = PipelineRunner()
            
            self.logger.info("🔧 Pipeline setup completed (without transport)")
            
        except Exception as e:
            self.logger.error(f"Failed to setup pipeline: {e}")
            raise

    async def _get_pipeline_components(self):
        
        pipeline_components = [
            self.transport.input(),
            self.stt,
            self.context_switch_processor,
            self.interview_gate_processor,  # Add gate here
            self.rtvi_processor,
            self.transcript_processor.user()]

        self.logger.info(f"Adding custom processor of length {len(self.custom_processors)}")
        pipeline_components.extend(self.custom_processors)
        
        pipeline_components.extend([
            self.context_aggregator.user(),
            self.interview_closure_handler,  # Add closure handler before LLM
            self.llm_service,
            self.tts,
            self.transport.output(),
            self.transcript_processor.assistant(),  # Place after transport.output() for assistant transcripts
            self.context_aggregator.assistant()
        ])

        return pipeline_components

        
    async def _setup_transport(self):
        """Setup WebRTC transport."""
        try:
            # Try to setup VAD, but make it optional
            vad_analyzer = None
            try:
                vad_analyzer = SileroVADAnalyzer(
                    params=VADParams(
                        confidence=0.7,      # Minimum confidence for voice detection
                        start_secs=0.2,      # Time to wait before confirming speech start
                        stop_secs=0.2,       # Time to wait before confirming speech stop
                        min_volume=0.6,      # Minimum volume threshold
                    )
                )
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
                vad_analyzer=vad_analyzer,
                turn_analyzer=LocalSmartTurnAnalyzerV3(params=SmartTurnParams()),
            )
            
            transportService = TransportService(provider="webrtc", webrtc_connection=self.webrtc_connection, params=transport_params)
            self.transport = transportService.setup_processor()
            
            self.logger.info("🔗 Transport setup completed")
            
        except Exception as e:
            self.logger.error(f"Failed to setup transport: {e}")
            raise
    
    async def _setup_llm_service(self):
        """Setup LLM service using Google API key with initial planner instructions."""
        try:
            google_key = settings.google_api_key
            if not google_key:
                raise ValueError("google_api_key not found in settings. Please check your config/local.env file")
            
            # Get initial planner instructions if interview context is available
            initial_instructions = self._get_initial_planner_instructions()
            
            try:
                from app.interview_playground.llm.llm_service import LLMService
                llm_service = LLMService(
                    provider="google", 
                    api_key=google_key, 
                    model="gemini-2.5-flash",
                    custom_instructions=initial_instructions
                )
                self.llm_service = llm_service.setup_processor()
                
                if initial_instructions:
                    self.logger.info("🤖 LLM service setup completed with initial planner instructions", 
                                   instructions_length=len(initial_instructions))
                else:
                    self.logger.info("🤖 LLM service setup completed with default instructions")
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
            
            self.context_aggregator = self.llm_service.create_context_aggregator(context, 
            user_params=LLMUserAggregatorParams(enable_emulated_vad_interruptions=True))
            
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

    async def _setup_custom_processor(self):
        """Setup RTVI processor for real-time voice interaction."""
        try:
            self.logger.info(f"🔧 Starting custom processors from service")
        
            # Get enabled processors from the processors service
            self.custom_processors = self.processors_service.setup_processors()

            self.logger.info(f"🔧 Setup {len(self.custom_processors)} processors from service")

            
        except Exception as e:
            self.logger.error(f"Failed to setup RTVI processor: {e}")
            raise
    
    async def _setup_context_switch_processor(self):
        """Setup Context Switch processor for managing LLM instruction transitions."""
        try:
            if not self.interview_context:
                self.logger.warning("No interview context available for context switch processor")
                return
            
            self.context_switch_processor = ContextSwitchProcessor(self.interview_context)
            self.logger.info("🔄 Context Switch processor setup completed")
            
        except Exception as e:
            self.logger.error(f"Failed to setup Context Switch processor: {e}")
            raise
    
    async def _setup_interview_gate_processor(self):
        """Setup Interview Gate Processor for frame filtering."""
        try:
            self.interview_gate_processor = InterviewGateProcessor()
            self.logger.info("🚪 Interview Gate Processor setup completed")
            
        except Exception as e:
            self.logger.error(f"Failed to setup Interview Gate Processor: {e}")
            raise
    
    async def _setup_interview_closure_handler(self):
        """Setup Interview Closure Handler for frame conversion."""
        try:
            self.interview_closure_handler = InterviewClosureHandler()
            self.logger.info("🔄 Interview Closure Handler setup completed")
            
        except Exception as e:
            self.logger.error(f"Failed to setup Interview Closure Handler: {e}")
            raise
    
    async def _setup_timer_monitor(self):
        """Setup Timer Monitor for managing interview phase timers."""
        try:
            if not self.interview_context:
                self.logger.warning("No interview context available for timer monitor")
                return
            
            # Create timer monitor with context processor and callback
            self.timer_monitor = InterviewTimerMonitor(
                interview_context=self.interview_context,
                context_processor=self.context_switch_processor,
                timer_callback=self._on_timer_event
            )
            
            # Set bot instance reference for SSE notifications
            self.timer_monitor.set_bot_instance_reference(self)
            
            self.logger.info("⏱️ Timer Monitor setup completed")
            
        except Exception as e:
            self.logger.error(f"Failed to setup Timer Monitor: {e}")
            raise
    
    async def _setup_transcript_processor(self):
        """Setup Transcript Processor for conversation transcription."""
        try:
            self.transcript_processor = self.transcript_service.setup_processor(self.interview_context)
            self.logger.info("📝 Transcript Processor setup completed",
                           session_id=self.interview_context.session_id if self.interview_context else "unknown")
            
        except Exception as e:
            self.logger.error(f"Failed to setup Transcript Processor: {e}")
            raise
    
    async def _start_initial_interview_phase(self):
        """Start the initial interview phase with first planner field."""
        try:
            if not self.interview_context or not self.timer_monitor:
                self.logger.info("Skipping initial phase start - missing components")
                return
            
            # Get the first planner field
            current_planner = self.interview_context.get_current_planner_field()
            if not current_planner:
                self.logger.warning("No planner fields available to start interview")
                return
            
            # Note: Initial instructions are already injected during LLM setup
            # No need to inject again here to avoid separate threads
            
            # Start the timer for the first planner
            timer_started = await self.timer_monitor.start_current_planner_timer()
            if timer_started:
                self.logger.info("🚀 Initial interview phase started", 
                               sequence=current_planner.sequence,
                               duration_minutes=current_planner.duration,
                               question_id=current_planner.question_id,
                               note="Instructions already loaded in LLM initialization")
            else:
                self.logger.error("Failed to start initial timer")
            
        except Exception as e:
            self.logger.error(f"Failed to start initial interview phase: {e}")
    
    def _get_initial_planner_instructions(self) -> str:
        """Get the initial planner field instructions for LLM initialization.
        
        Returns:
            Initial planner instructions or None if not available
        """
        try:
            if not self.interview_context:
                self.logger.debug("No interview context available for initial instructions")
                return None
            
            # Get the first planner field (sequence 0)
            current_planner = self.interview_context.get_current_planner_field()
            if not current_planner:
                self.logger.debug("No current planner field available for initial instructions")
                return None
            
            instructions = current_planner.interview_instructions
            if not instructions or instructions.strip() == "":
                self.logger.debug("No instructions in first planner field, will use defaults")
                return None
            
            # Format the instructions with context information
            formatted_instructions = self._format_initial_instructions(instructions, current_planner)
            
            self.logger.info("Retrieved initial planner instructions", 
                           sequence=current_planner.sequence,
                           question_id=current_planner.question_id,
                           duration_minutes=current_planner.duration,
                           instructions_length=len(formatted_instructions))
            
            return formatted_instructions
            
        except Exception as e:
            self.logger.error(f"Error getting initial planner instructions: {e}")
            return None
    
    def _format_initial_instructions(self, instructions: str, planner_field) -> str:
        """Format initial instructions with context information.
        
        Args:
            instructions: Raw instructions from planner field
            planner_field: The planner field containing the instructions
            
        Returns:
            Formatted instructions string
        """
        session_info = f"""
--- INTERVIEW SESSION CONTEXT ---

Interview ID: {self.interview_context.mock_interview_id}
Session ID: {self.interview_context.session_id}
Current Phase: {planner_field.sequence + 1} of {len(self.interview_context.planner_fields)}
Phase Duration: {planner_field.duration} minutes
Question ID: {planner_field.question_id}

--- PHASE INSTRUCTIONS ---

{instructions}

--- END CONTEXT ---

Please begin the interview following these specific instructions for this phase.
"""
        return session_info
    
    async def _on_timer_event(self, event_type: str, event_data: dict):
        """Handle timer events from the timer monitor.
        
        Args:
            event_type: Type of timer event (timer_started, timer_expired, etc.)
            event_data: Event-specific data
        """
        try:
            self.logger.info(f"🔔 Timer event received: {event_type}", 
                           event_type=event_type, 
                           event_data_keys=list(event_data.keys()) if event_data else [],
                           **event_data)
            
            if event_type == "timer_started":
                planner_field = event_data.get("planner_field")
                if planner_field:
                    self.interview_phase = f"phase_{planner_field.sequence}"
            
            elif event_type == "timer_expired":
                completed_planner = event_data.get("completed_planner")
                if completed_planner:
                    self.logger.info("Phase completed", 
                                   sequence=completed_planner.sequence,
                                   question_id=completed_planner.question_id)
            
            elif event_type == "planner_transitioned":
                new_planner = event_data.get("new_planner")
                transition_count = event_data.get("transition_count", 0)
                if new_planner:
                    self.interview_phase = f"phase_{new_planner.sequence}"
                    self.logger.info("Transitioned to new phase", 
                                   new_sequence=new_planner.sequence,
                                   question_id=new_planner.question_id,
                                   total_transitions=transition_count)
            
            elif event_type == "interview_finalized":
                total_transitions = event_data.get("total_transitions", 0)
                session_duration = event_data.get("session_duration_seconds", 0)
                self.interview_phase = "completed"
                self.logger.info("Interview completed", 
                               total_phases=total_transitions + 1,
                               session_duration_minutes=session_duration // 60)
                
                # Activate the gate to block future frames
                if self.interview_gate_processor:
                    self.interview_gate_processor.mark_interview_completed()
                    self.logger.info("🚪 Interview gate activated - blocking user/data frames")
                
                # Stop LLM from generating new responses after interview completion
                await self._stop_llm_after_completion()
            
        except Exception as e:
            self.logger.error(f"Error handling timer event: {e}", event_type=event_type)
    
    async def _stop_llm_after_completion(self):
        """Mark interview as completed and let context switch processor handle the final message."""
        try:
            self.logger.info("🛑 Interview completion processed", room_id=self.room_id)
            
            # Mark that the interview is completed
            # The context switch processor will handle the final closing message
            self._final_message_sent = True
            
            self.logger.info("✅ Interview marked as completed", room_id=self.room_id)
            
        except Exception as e:
            self.logger.error(f"Failed to process interview completion: {e}", room_id=self.room_id)
    
    async def _setup_event_handlers(self):
        """Setup all event handlers."""

        # RTVI event handlers
        @self.rtvi_processor.event_handler("on_client_ready")
        async def on_client_ready(rtvi):
            self.logger.info("Pipecat client ready.")
            await rtvi.set_bot_ready()
        
        @self.rtvi_processor.event_handler("on_client_message")
        async def on_client_message(rtvi, message):
            """Handle client messages and forward them to our CodeContextProcessor"""
            self.logger.info(f"RTVI client message received: {message}")
        
        # Transport event handlers
        @self.transport.event_handler("on_client_connected")
        async def on_client_connected(transport, client):
            self.logger.info("Pipecat Client connected")
            # Kick off the conversation
            await self.task.queue_frames([self.context_aggregator.user().get_context_frame()])
        
        @self.transport.event_handler("on_client_disconnected")
        async def on_client_disconnected(transport, client):
            self.logger.info("Pipecat Client disconnected")
            self.logger.info(f"Final Context Details : {self.context_aggregator}")
            
            # Cleanup without closing transport again (already disconnected)
            try:
                # Stop timer monitor
                if self.timer_monitor:
                    await self.timer_monitor.stop_current_timer()
                    self.logger.info("Timer monitor stopped")
                
                # Publish session ended event
                if self.transcript_processor:
                    await self.transcript_processor.publish_session_ended()
                
                # Cancel the pipeline task (PipelineRunner doesn't have stop method)
                if self.task:
                    await self.task.cancel()
                    self.logger.info("Pipeline task cancelled")
                
                self.is_running = False
                self.logger.info("Cleanup completed on disconnect")
                
            except Exception as e:
                self.logger.error(f"Error during disconnect cleanup: {e}")
        
        self.logger.info("🎭 Event handlers setup completed")
    
    async def run(self):
        """Run the interview bot."""
        try:
            if not all([self.transport, self.rtvi_processor, self.pipeline, self.task, self.runner]):
                raise RuntimeError("Bot not properly initialized")
            
            self.is_running = True
            self.logger.info(f"🚀 Starting interview bot for room_id: {self.room_id}")
            
            # Publish session started event
            if self.transcript_processor:
                await self.transcript_processor.publish_session_started()
            
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
            # Publish session ended event
            if self.transcript_processor:
                await self.transcript_processor.publish_session_ended()
            
            # Stop timer monitor first
            if self.timer_monitor:
                await self.timer_monitor.stop_current_timer()
                self.logger.info("Timer monitor stopped")
            
            # Cancel the pipeline task (PipelineRunner doesn't have stop method)
            if self.task:
                await self.task.cancel()
                self.logger.info("Pipeline task cancelled")
            
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
        status = {
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
                "pipeline": self.pipeline is not None,
                "context_switch_processor": self.context_switch_processor is not None,
                "timer_monitor": self.timer_monitor is not None,
                "interview_gate_processor": self.interview_gate_processor is not None,
                "interview_closure_handler": self.interview_closure_handler is not None
            }
        }
        
        # Add timer status if available
        if self.timer_monitor:
            status["timer_status"] = self.timer_monitor.get_timer_status()
        
        # Add context switch processor status if available
        if self.context_switch_processor:
            status["context_processor_status"] = self.context_switch_processor.get_processor_status()
        
        # Add interview context summary if available
        if self.interview_context:
            status["interview_context"] = self.interview_context.get_context_summary()
        
        return status
    
    async def get_timer_status(self) -> dict:
        """Get detailed timer status."""
        if not self.timer_monitor:
            return {"error": "Timer monitor not available"}
        
        return self.timer_monitor.get_timer_status()
    
    async def pause_timer(self) -> bool:
        """Pause the current timer."""
        if not self.timer_monitor:
            self.logger.warning("Timer monitor not available for pause")
            return False
        
        return await self.timer_monitor.pause_timer()
    
    async def resume_timer(self) -> bool:
        """Resume the paused timer."""
        if not self.timer_monitor:
            self.logger.warning("Timer monitor not available for resume")
            return False
        
        return await self.timer_monitor.resume_timer()
    
    async def skip_to_next_phase(self) -> bool:
        """Manually skip to the next interview phase."""
        try:
            if not self.timer_monitor:
                self.logger.warning("Timer monitor not available for phase skip")
                return False
            
            # Stop current timer and transition
            await self.timer_monitor.stop_current_timer()
            await self.timer_monitor.transition_to_next_planner()
            
            self.logger.info("Manually skipped to next interview phase")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to skip to next phase: {e}")
            return False
