"""
Transport service for creating and managing transport implementations.
"""

from app.interview_playground.transport.webrtc_transport import WebRTCTransport
from app.interview_playground.transport.daily_transport import DailyTransportImpl


class TransportService:
    """Service for creating transport implementations."""
    
    def __init__(self, provider: str = "webrtc", **kwargs):
        """Initialize Transport service.
        
        Args:
            provider: Transport provider name
            **kwargs: Provider-specific arguments
        """
        self.provider = provider
        self.kwargs = kwargs
        self._transport_instance = None
            
    def setup_processor(self):
        """Setup the transport processor based on configured provider.
        
        Returns:
            FrameProcessor instance
        """
        if not self._transport_instance:
            provider = self.provider.lower()
            if provider == "webrtc":
                webrtc_connection = self.kwargs.get("webrtc_connection")
                if not webrtc_connection:
                    raise ValueError("webrtc_connection is required for WebRTC transport")
                
                # Pass through the params if provided, otherwise use individual parameters
                params = self.kwargs.get("params")
                video_in_enabled = self.kwargs.get("video_in_enabled", False)
                video_out_enabled = self.kwargs.get("video_out_enabled", False)
                video_out_is_live = self.kwargs.get("video_out_is_live", False)
                audio_in_enabled = self.kwargs.get("audio_in_enabled", True)
                audio_out_enabled = self.kwargs.get("audio_out_enabled", True)
                vad_analyzer = self.kwargs.get("vad_analyzer")
                
                self._transport_instance = WebRTCTransport(
                    webrtc_connection=webrtc_connection,
                    params=params,  # Pass the TransportParams object
                    video_in_enabled=video_in_enabled,
                    video_out_enabled=video_out_enabled,
                    video_out_is_live=video_out_is_live,
                    audio_in_enabled=audio_in_enabled,
                    audio_out_enabled=audio_out_enabled,
                    vad_analyzer=vad_analyzer
                )
            elif provider == "daily":
                room_url = self.kwargs.get("room_url")
                token = self.kwargs.get("token")
                params = self.kwargs.get("params")

                if not room_url or not token:
                    raise ValueError("room_url and token are required for Daily transport")

                self._transport_instance = DailyTransportImpl(
                    room_url=room_url,
                    token=token,
                    params=params,
                    audio_in_enabled=self.kwargs.get("audio_in_enabled", True),
                    audio_out_enabled=self.kwargs.get("audio_out_enabled", True),
                    transcription_enabled=self.kwargs.get("transcription_enabled", True),
                )
            else:
                raise ValueError(f"Unknown transport provider: {self.provider}")
                
        return self._transport_instance.setup_processor()
