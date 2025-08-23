import time
import json
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import structlog
from uuid import uuid4

logger = structlog.get_logger()


class LoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid4())
        start_time = time.time()
        
        # Create flat log data structure
        log_data = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent", "")[:100],  # Truncate long user agents
        }

        # Add query parameters if any
        if request.query_params:
            log_data["query_params"] = dict(request.query_params)

        # Add request body for POST/PUT/PATCH requests
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body:
                    content_type = request.headers.get("content-type", "")
                    if "application/json" in content_type:
                        try:
                            body_data = json.loads(body.decode())
                            # Flatten body data for better readability
                            if isinstance(body_data, dict):
                                for key, value in body_data.items():
                                    if isinstance(value, (str, int, float, bool)):
                                        log_data[f"body_{key}"] = value
                                    elif isinstance(value, list) and len(value) <= 3:
                                        log_data[f"body_{key}"] = value
                                    else:
                                        log_data[f"body_{key}"] = str(value)[:100]  # Truncate long values
                            else:
                                log_data["body"] = str(body_data)[:200]
                        except json.JSONDecodeError:
                            log_data["body"] = body.decode()[:200]
                    else:
                        log_data["body"] = body.decode()[:200]
            except Exception as e:
                log_data["body_error"] = str(e)

        # Log request start with flat structure
        logger.info("API Request Started", **log_data)

        request.state.request_id = request_id
        request.state.start_time = start_time

        try:
            response = await call_next(request)
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                "API Request Failed",
                request_id=request_id,
                path=request.url.path,
                method=request.method,
                error=str(e),
                process_time=round(process_time, 4)
            )
            raise

        process_time = time.time() - start_time

        # Log response completion with flat structure
        response_log_data = {
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "status_code": response.status_code,
            "process_time": round(process_time, 4),
        }

        if response.status_code >= 400:
            logger.warning("API Request Completed with Error", **response_log_data)
        else:
            logger.info("API Request Completed Successfully", **response_log_data)

        response.headers["X-Request-ID"] = request_id
        return response


class StructlogMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        request_id = getattr(request.state, "request_id", str(uuid4()))
        
        # Clear and set context variables for structured logging
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            path=request.url.path,
            method=request.method
        )

        response = await call_next(request)
        return response