from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    database_url: str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 30
    log_level: str = "INFO"
    environment: str = "local"
    api_prefix: str = "/interview/api/v1"
    cors_origins: List[str] = ["*"]
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

    class Config:
        env_file = f"config/{os.getenv('ENV', 'local')}.env"
        case_sensitive = False


settings = Settings()