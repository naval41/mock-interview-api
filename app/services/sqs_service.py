"""
AWS SQS Service for sending interview completion notifications.
"""

import json
from typing import Dict, Any
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from app.core.config import settings
import structlog

logger = structlog.get_logger()


class SQSService:
    """Service for sending messages to AWS SQS queues."""
    
    def __init__(self):
        """Initialize SQS client with AWS credentials from settings."""
        self.queue_url = settings.sqs_interview_completion_queue_url
        self.region = settings.aws_region
        
        # Initialize SQS client only if credentials are provided
        self.sqs_client = None
        self._initialize_client()
        
        logger.info("SQSService initialized",
                   region=self.region,
                   queue_url=self.queue_url,
                   enabled=self.is_enabled())
    
    def _initialize_client(self):
        """Initialize boto3 SQS client with credentials."""
        try:
            # Only initialize if we have credentials
            if (settings.aws_access_key_id and 
                settings.aws_secret_access_key and 
                self.queue_url):
                
                self.sqs_client = boto3.client(
                    'sqs',
                    region_name=self.region,
                    aws_access_key_id=settings.aws_access_key_id,
                    aws_secret_access_key=settings.aws_secret_access_key
                )
                logger.info("SQS client initialized successfully")
            else:
                logger.warning("SQS credentials not configured - notifications will be disabled",
                             has_access_key=bool(settings.aws_access_key_id),
                             has_secret_key=bool(settings.aws_secret_access_key),
                             has_queue_url=bool(self.queue_url))
        except Exception as e:
            logger.error("Failed to initialize SQS client",
                        error=str(e),
                        error_type=type(e).__name__)
            self.sqs_client = None
    
    def is_enabled(self) -> bool:
        """Check if SQS service is enabled and properly configured.
        
        Returns:
            True if SQS client is initialized and ready to send messages
        """
        return self.sqs_client is not None
    
    async def send_interview_completion_notification(
        self,
        candidate_interview_id: str
    ) -> Dict[str, Any]:
        """Send interview completion notification to SQS queue.
        
        Args:
            candidate_interview_id: ID of the candidate interview
            
        Returns:
            Dictionary with status and message details
        """
        # Check if SQS is enabled
        if not self.is_enabled():
            logger.warning("SQS service not enabled - skipping notification",
                          candidate_interview_id=candidate_interview_id)
            return {
                "success": False,
                "message": "SQS service not configured",
                "notification_sent": False
            }
        
        # Prepare simplified message payload - only candidate_interview_id
        message_payload = {
            "candidateInterviewId": candidate_interview_id
        }
        
        try:
            # Send message to SQS with only candidate_interview_id
            response = self.sqs_client.send_message(
                QueueUrl=self.queue_url,
                MessageBody=json.dumps(message_payload),
                MessageAttributes={
                    'candidateInterviewId': {
                        'StringValue': candidate_interview_id,
                        'DataType': 'String'
                    }
                }
            )
            
            message_id = response.get('MessageId')
            
            logger.info("✅ Interview completion notification sent to SQS",
                       message_id=message_id,
                       candidate_interview_id=candidate_interview_id,
                       queue_url=self.queue_url)
            
            return {
                "success": True,
                "message": "Notification sent successfully",
                "message_id": message_id,
                "notification_sent": True
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            logger.error("AWS SQS ClientError - failed to send notification",
                        error_code=error_code,
                        error_message=error_message,
                        candidate_interview_id=candidate_interview_id,
                        queue_url=self.queue_url)
            
            return {
                "success": False,
                "message": f"SQS ClientError: {error_code} - {error_message}",
                "notification_sent": False
            }
            
        except BotoCoreError as e:
            logger.error("AWS BotoCoreError - failed to send notification",
                        error=str(e),
                        candidate_interview_id=candidate_interview_id,
                        queue_url=self.queue_url)
            
            return {
                "success": False,
                "message": f"BotoCoreError: {str(e)}",
                "notification_sent": False
            }
            
        except Exception as e:
            logger.error("Unexpected error sending SQS notification",
                        error=str(e),
                        error_type=type(e).__name__,
                        candidate_interview_id=candidate_interview_id)
            
            return {
                "success": False,
                "message": f"Unexpected error: {str(e)}",
                "notification_sent": False
            }
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get current status of SQS service.
        
        Returns:
            Dictionary containing service status information
        """
        return {
            "enabled": self.is_enabled(),
            "region": self.region,
            "queue_url": self.queue_url if self.queue_url else "Not configured",
            "client_initialized": self.sqs_client is not None
        }


# Create singleton instance
sqs_service = SQSService()

