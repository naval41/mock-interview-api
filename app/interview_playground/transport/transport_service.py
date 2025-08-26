"""
Transport service for creating and managing transport implementations.
"""

from app.interview_playground.transport.base_transport import BaseTransport
from app.interview_playground.transport.webrtc_transport import WebRTCTransport


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
        
    def create_webrtc(self, webrtc_connection, video_in_enabled: bool = False,
                      video_out_enabled: bool = False, video_out_is_live: bool = False,
                      audio_in_enabled: bool = True, audio_out_enabled: bool = True,
                      vad_analyzer=None) -> BaseTransport:
        """Create a WebRTC Transport instance.
        
        Args:
            webrtc_connection: WebRTC connection object
            video_in_enabled: Whether video input is enabled
            video_out_enabled: Whether video output is enabled
            video_out_is_live: Whether video output is live
            audio_in_enabled: Whether audio input is enabled
            audio_out_enabled: Whether audio output is enabled
            vad_analyzer: Voice Activity Detection analyzer
            
        Returns:
            WebRTCTransport instance
        """
        return WebRTCTransport(
            webrtc_connection=webrtc_connection,
            video_in_enabled=video_in_enabled,
            video_out_enabled=video_out_enabled,
            video_out_is_live=video_out_is_live,
            audio_in_enabled=audio_in_enabled,
            audio_out_enabled=audio_out_enabled,
            vad_analyzer=vad_analyzer
        )
        
    def create(self, provider: str, **kwargs) -> BaseTransport:
        """Create a transport instance based on provider.
        
        Args:
            provider: Transport provider name
            **kwargs: Provider-specific arguments
            
        Returns:
            BaseTransport instance
        """
        if provider.lower() == "webrtc":
            webrtc_connection = kwargs.get("webrtc_connection")
            if not webrtc_connection:
                raise ValueError("webrtc_connection is required for WebRTC transport")
                
            video_in_enabled = kwargs.get("video_in_enabled", False)
            video_out_enabled = kwargs.get("video_out_enabled", False)
            video_out_is_live = kwargs.get("video_out_is_live", False)
            audio_in_enabled = kwargs.get("audio_in_enabled", True)
            audio_out_enabled = kwargs.get("audio_out_enabled", True)
            vad_analyzer = kwargs.get("vad_analyzer")
            
            return self.create_webrtc(
                webrtc_connection=webrtc_connection,
                video_in_enabled=video_in_enabled,
                video_out_enabled=video_out_enabled,
                video_out_is_live=video_out_is_live,
                audio_in_enabled=audio_in_enabled,
                audio_out_enabled=audio_out_enabled,
                vad_analyzer=vad_analyzer
            )
        else:
            raise ValueError(f"Unknown transport provider: {provider}")
            
    def setup_processor(self):
        """Setup the transport processor based on configured provider.
        
        Returns:
            FrameProcessor instance
        """
        if not self._transport_instance:
            if self.provider.lower() == "webrtc":
                webrtc_connection = self.kwargs.get("webrtc_connection")
                if not webrtc_connection:
                    raise ValueError("webrtc_connection is required for WebRTC transport")
                    
                video_in_enabled = self.kwargs.get("video_in_enabled", False)
                video_out_enabled = self.kwargs.get("video_out_enabled", False)
                video_out_is_live = self.kwargs.get("video_out_is_live", False)
                audio_in_enabled = self.kwargs.get("audio_in_enabled", True)
                audio_out_enabled = self.kwargs.get("audio_out_enabled", True)
                vad_analyzer = self.kwargs.get("vad_analyzer")
                
                self._transport_instance = self.create_webrtc(
                    webrtc_connection=webrtc_connection,
                    video_in_enabled=video_in_enabled,
                    video_out_enabled=video_out_enabled,
                    video_out_is_live=video_out_is_live,
                    audio_in_enabled=audio_in_enabled,
                    audio_out_enabled=audio_out_enabled,
                    vad_analyzer=vad_analyzer
                )
            else:
                raise ValueError(f"Unknown transport provider: {self.provider}")
                
        return self._transport_instance.setup_processor()
