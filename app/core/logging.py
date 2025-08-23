import logging
import structlog
from app.core.config import settings


def setup_logging():
    """
    Setup structured logging with flat, readable format.
    """
    # Configure structlog for flat logging
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            # Use a custom formatter for flat logs instead of JSONRenderer
            structlog.dev.ConsoleRenderer(colors=False)
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard logging to use simple format
    formatter = logging.Formatter(
        '%(asctime)s | %(name)s | %(levelname)s | %(message)s'
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, settings.log_level.upper()))

        # Set uvicorn logger level
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.setLevel(getattr(logging, settings.log_level.upper()))
    
    # Disable verbose DEBUG logs from aiortc and other WebRTC libraries if configured
    if settings.disable_webrtc_debug:
        aiortc_logger = logging.getLogger("aiortc")
        aiortc_logger.setLevel(logging.WARNING)
        
        # Disable other noisy WebRTC-related loggers
        webrtc_loggers = [
            "aiortc.rtcrtpreceiver",
            "aiortc.rtcrtpsender", 
            "aiortc.rtcpeerconnection",
            "aiortc.mediastreams",
            "aioice",
            "av"
        ]
        
        for logger_name in webrtc_loggers:
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.WARNING)
    
    return structlog.get_logger()