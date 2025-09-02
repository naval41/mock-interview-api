from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn

from app.core.config import settings
from app.core.database import create_db_and_tables, close_db
from app.core.logging import setup_logging
from app.middleware.logging_middleware import LoggingMiddleware, StructlogMiddleware
from app.controllers import auth_controller, interview_controller, candidate_interview_controller, candidate_interview_planner_controller
from app.services.pipecat_service import pipecat_service

import structlog

logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup", environment=settings.environment)
    try:
        await create_db_and_tables()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))
        raise
    
    yield
    
    logger.info("Application shutdown")
    try:
        # Clean up pipecat connections
        await pipecat_service.cleanup_all()
        logger.info("Pipecat connections cleaned up")
        
        # Close database connections
        await close_db()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error("Error during shutdown", error=str(e))


app = FastAPI(
    title="Mock Interview API",
    description="A Roundz Mock Interview API with Pipecat Integration",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.environment == "local" else None,
    redoc_url="/redoc" if settings.environment == "local" else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or specify: ["http://localhost:3000", "https://yourdomain.com"]
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods: GET, POST, etc.
    allow_headers=["*"],  # Allow all headers
)

# app.add_middleware(StructlogMiddleware)
# app.add_middleware(LoggingMiddleware)

app.include_router(auth_controller.router, prefix=settings.api_prefix)
app.include_router(interview_controller.router, prefix="")
app.include_router(candidate_interview_controller.router, prefix=settings.api_prefix)
app.include_router(candidate_interview_planner_controller.router, prefix=settings.api_prefix)


@app.get("/")
async def root():
    return {
        "message": "Mock Interview API is running",
        "version": "1.0.0",
        "environment": settings.environment,
                    "features": ["JWT Authentication", "Pipecat Integration", "Real-time Interviews", "Phase Management"],
        "docs_url": "/docs" if settings.environment == "local" else "Documentation disabled in production"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "environment": settings.environment,
        "pipecat_connections": len(pipecat_service.connections),
        "active_bots": len(pipecat_service.bot_instances)
    }


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    logger.warning(
        "HTTP Exception",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path,
        method=request.method
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "message": exc.detail,
            "success": False,
            "status_code": exc.status_code
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(
        "Unhandled Exception",
        error=str(exc),
        path=request.url.path,
        method=request.method
    )
    return JSONResponse(
        status_code=500,
        content={
            "message": "Internal server error",
            "success": False,
            "status_code": 500
        }
    )


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.environment == "local",
        log_config=None
    )