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
        
        request_data = {
            "request_id": request_id,
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "headers": dict(request.headers),
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
        }

        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body:
                    content_type = request.headers.get("content-type", "")
                    if "application/json" in content_type:
                        try:
                            request_data["body"] = json.loads(body.decode())
                        except json.JSONDecodeError:
                            request_data["body"] = body.decode()
                    else:
                        request_data["body"] = body.decode()
            except Exception as e:
                logger.warning("Could not read request body", request_id=request_id, error=str(e))

        logger.info("API Request Started", **request_data)

        request.state.request_id = request_id
        request.state.start_time = start_time

        try:
            response = await call_next(request)
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                "API Request Failed",
                request_id=request_id,
                error=str(e),
                process_time=process_time,
                path=request.url.path,
                method=request.method
            )
            raise

        process_time = time.time() - start_time

        response_data = {
            "request_id": request_id,
            "status_code": response.status_code,
            "process_time": round(process_time, 4),
            "path": request.url.path,
            "method": request.method,
        }

        if response.status_code >= 400:
            logger.warning("API Request Completed with Error", **response_data)
        else:
            logger.info("API Request Completed Successfully", **response_data)

        response.headers["X-Request-ID"] = request_id
        return response


class StructlogMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        request_id = getattr(request.state, "request_id", str(uuid4()))
        
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            path=request.url.path,
            method=request.method
        )

        response = await call_next(request)
        return response