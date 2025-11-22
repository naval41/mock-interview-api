# pyright: reportMissingImports=false

"""
Daily Transport implementation that wraps Daily.co meeting transport.
"""

from typing import Optional
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.processors.frame_processor import FrameProcessor
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.turn.smart_turn.base_smart_turn import SmartTurnParams
from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3

from app.interview_playground.transport.base_transport import BaseTransport
from pipecat.transports.daily.transport import DailyParams, DailyTransport


class DailyTransportImpl(BaseTransport):
    """Daily Transport implementation."""

    def __init__(
        self,
        room_url: str,  
        token: str,
        params: Optional[DailyParams] = None,
        audio_in_enabled: bool = True,
        audio_out_enabled: bool = True,
        transcription_enabled: bool = True,
    ) -> None:
        self.room_url = room_url
        self.token = token
        self.params = params
        self.audio_in_enabled = audio_in_enabled
        self.audio_out_enabled = audio_out_enabled
        self.transcription_enabled = transcription_enabled

        self._transport_instance: Optional[DailyTransport] = None

    def setup_processor(self) -> FrameProcessor:
        """Setup the Daily Transport FrameProcessor instance."""

        if self.params is None:
            self.params = DailyParams(
                audio_in_enabled=self.audio_in_enabled,
                audio_out_enabled=self.audio_out_enabled,
                transcription_enabled=self.transcription_enabled,
                vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.2)),
                turn_analyzer=LocalSmartTurnAnalyzerV3(params=SmartTurnParams()),
            )

        transport = DailyTransport(
            room_url=self.room_url,
            token=self.token,
            bot_name='Alex',
            params=self.params,
        )

        self._transport_instance = transport
        return transport

    def get_status(self) -> dict:
        """Get the current status of the transport."""
        return {
            "room_url": self.room_url,
            "audio_in_enabled": self.audio_in_enabled,
            "audio_out_enabled": self.audio_out_enabled,
            "transcription_enabled": self.transcription_enabled,
            "has_custom_params": self.params is not None,
        }

