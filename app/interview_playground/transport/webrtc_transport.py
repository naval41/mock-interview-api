"""
WebRTC Transport implementation that extends BaseTransport.
"""

from pipecat.processors.frame_processor import FrameProcessor
from app.interview_playground.transport.base_transport import BaseTransport


class WebRTCTransport(BaseTransport):
    """WebRTC Transport implementation."""
    
    def __init__(self, webrtc_connection, params=None, video_in_enabled: bool = False, 
                 video_out_enabled: bool = False, video_out_is_live: bool = False,
                 audio_in_enabled: bool = True, audio_out_enabled: bool = True,
                 vad_analyzer=None):
        """Initialize WebRTC Transport.
        
        Args:
            webrtc_connection: WebRTC connection object
            params: Optional TransportParams object (includes turn_analyzer, vad_analyzer, etc)
            video_in_enabled: Whether video input is enabled
            video_out_enabled: Whether video output is enabled
            video_out_is_live: Whether video output is live
            audio_in_enabled: Whether audio input is enabled
            audio_out_enabled: Whether audio output is enabled
            vad_analyzer: Voice Activity Detection analyzer
        """
        self.webrtc_connection = webrtc_connection
        self.params = params  # Store the complete params if provided
        self.video_in_enabled = video_in_enabled
        self.video_out_enabled = video_out_enabled
        self.video_out_is_live = video_out_is_live
        self.audio_in_enabled = audio_in_enabled
        self.audio_out_enabled = audio_out_enabled
        self.vad_analyzer = vad_analyzer
        self._transport_instance = None
        
    def setup_processor(self) -> FrameProcessor:
        """Setup the WebRTC Transport FrameProcessor instance.
        
        Returns:
            FrameProcessor configured for WebRTC Transport
        """
        from pipecat.transports.network.small_webrtc import SmallWebRTCTransport
        from pipecat.transports.base_transport import TransportParams
        
        # If params was provided (with turn_analyzer), use it directly
        # Otherwise create new TransportParams from individual properties
        if self.params:
            transport_params = self.params
        else:
            transport_params = TransportParams(
                video_in_enabled=self.video_in_enabled,
                video_out_enabled=self.video_out_enabled,
                video_out_is_live=self.video_out_is_live,
                audio_in_enabled=self.audio_in_enabled,
                audio_out_enabled=self.audio_out_enabled,
                vad_analyzer=self.vad_analyzer,
            )
        
        processor = SmallWebRTCTransport(
            webrtc_connection=self.webrtc_connection, 
            params=transport_params
        )
        
        return processor
            
    def get_status(self) -> dict:
        """Get the current status of the transport.
        
        Returns:
            Dictionary containing transport status information
        """
        return {
            "video_in_enabled": self.video_in_enabled,
            "video_out_enabled": self.video_out_enabled,
            "video_out_is_live": self.video_out_is_live,
            "audio_in_enabled": self.audio_in_enabled,
            "audio_out_enabled": self.audio_out_enabled,
            "vad_analyzer": self.vad_analyzer is not None,
            "webrtc_connection": self.webrtc_connection is not None
        }
