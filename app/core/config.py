from pydantic_settings import BaseSettings
from typing import List, Union
import os
import json
import re


class Settings(BaseSettings):
    database_url: str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 30
    log_level: str = "INFO"
    environment: str = "local"
    api_prefix: str = "/interview/api/v1"
    # CORS origins - can be JSON array or comma-separated string
    # For localhost wildcard, use "localhost:*" which will match any port
    cors_origins: Union[List[str], str] = ["localhost:*", "https://roundz.ai"]
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_schema: str = "public"
    
    # Pipecat API Keys
    deepgram_api_key: str = ""
    google_api_key: str = ""

    # Daily.co integration
    daily_api_key: str = ""
    daily_api_base_url: str = "https://api.daily.co/v1"
    daily_room_domain: str = ""

    # Encryption
    encryption_key: str = ""
    
    # AWS SQS Configuration
    aws_region: str = "ap-south-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    sqs_interview_completion_queue_url: str = ""
    
    # Logging control
    disable_webrtc_debug: bool = True

    @classmethod
    def parse_env_var(cls, field_name: str, raw_val: str) -> any:
        """Custom parser for CORS_ORIGINS to handle JSON, comma-separated, and wildcard formats."""
        if field_name == 'cors_origins':
            # Try JSON first
            try:
                parsed = json.loads(raw_val)
                return parsed if isinstance(parsed, list) else [parsed]
            except (json.JSONDecodeError, ValueError):
                # Fall back to comma-separated
                return [origin.strip() for origin in raw_val.split(",") if origin.strip()]
        return cls.json_loads(raw_val) if hasattr(cls, 'json_loads') else raw_val
    
    def get_cors_origins_list(self) -> List[str]:
        """Get CORS origins as a list, handling wildcard localhost patterns."""
        if isinstance(self.cors_origins, str):
            # Try to parse as JSON
            try:
                origins = json.loads(self.cors_origins)
            except (json.JSONDecodeError, ValueError):
                # Comma-separated
                origins = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        else:
            origins = self.cors_origins
        
        return origins if isinstance(origins, list) else [origins]

    class Config:
        env_file = f"config/{os.getenv('ENV', 'local')}.env"
        case_sensitive = False


settings = Settings()


def is_origin_allowed(origin: str) -> bool:
    """
    Custom origin validator that supports localhost wildcard ports.
    
    Supports:
    - "localhost:*" - matches any localhost port (http://localhost:3000, http://localhost:5000, etc.)
    - "127.0.0.1:*" - matches any 127.0.0.1 port
    - Specific origins like "https://roundz.ai"
    """
    if not origin:
        return False
    
    allowed_origins = settings.get_cors_origins_list()
    
    # Check exact matches first
    if origin in allowed_origins:
        return True
    
    # Check for localhost wildcard patterns
    for allowed in allowed_origins:
        if allowed == "localhost:*":
            # Match http://localhost:PORT or https://localhost:PORT
            if re.match(r'^https?://localhost(:\d+)?/?$', origin):
                return True
        elif allowed == "127.0.0.1:*":
            # Match http://127.0.0.1:PORT or https://127.0.0.1:PORT
            if re.match(r'^https?://127\.0\.0\.1(:\d+)?/?$', origin):
                return True
        elif "*" in allowed:
            # Generic wildcard pattern support (convert to regex)
            pattern = allowed.replace("*", ".*")
            if re.match(f"^{pattern}$", origin):
                return True
    
    return False