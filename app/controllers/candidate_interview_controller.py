from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_async_session
from app.core.security import validate_request
from app.services.candidate_interview_service import candidate_interview_service
from app.models.candidate_interview import (
    CandidateInterview, 
    CandidateInterviewCreate, 
    CandidateInterviewRead, 
    CandidateInterviewUpdate
)
from app.models.enums import CandidateInterviewStatus
from typing import List
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/candidate-interviews", tags=["Candidate Interviews"])


@router.post("/", response_model=CandidateInterviewRead)
async def create_candidate_interview(
    interview: CandidateInterviewCreate,
    current_user=Depends(validate_request)
):
    """Create a new candidate interview"""
    try:
        user_id = current_user.get("user_id")
        
        # Create the interview using service
        interview_data = interview.dict()
        created_interview = await candidate_interview_service.create_candidate_interview(interview_data, user_id)
        
        return created_interview
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Failed to create candidate interview", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create candidate interview"
        )


@router.get("/", response_model=List[CandidateInterviewRead])
async def get_candidate_interviews(
    skip: int = 0,
    limit: int = 100
):
    """Get all candidate interviews for the current user"""
    try:
        user_id = '1'
        interviews = await candidate_interview_service.get_user_interviews(user_id, skip, limit)
        
        return interviews
        
    except Exception as e:
        logger.error("Failed to get candidate interviews", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get candidate interviews"
        )


@router.get("/{interview_id}", response_model=CandidateInterviewRead)
async def get_candidate_interview(
    interview_id: str,
    current_user=Depends(validate_request)
):
    """Get a specific candidate interview by ID"""
    try:
        user_id = current_user.get("user_id")
        interview = await candidate_interview_service.get_candidate_interview(interview_id, user_id)
        
        return interview
        
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        elif "not authorized" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e)
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
    except Exception as e:
        logger.error("Failed to get candidate interview", interview_id=interview_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get candidate interview"
        )


@router.put("/{interview_id}", response_model=CandidateInterviewRead)
async def update_candidate_interview(
    interview_id: str,
    interview_update: CandidateInterviewUpdate,
    current_user=Depends(validate_request)
):
    """Update a candidate interview"""
    try:
        user_id = current_user.get("user_id")
        
        # Update the interview using service
        update_data = interview_update.dict(exclude_unset=True)
        updated_interview = await candidate_interview_service.update_candidate_interview(
            interview_id, update_data, user_id
        )
        
        return updated_interview
        
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        elif "not authorized" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e)
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
    except Exception as e:
        logger.error("Failed to update candidate interview", interview_id=interview_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update candidate interview"
        )


@router.patch("/{interview_id}/status")
async def update_interview_status(
    interview_id: str,
    status: CandidateInterviewStatus,
    current_user=Depends(validate_request)
):
    """Update the status of a candidate interview"""
    try:
        user_id = current_user.get("user_id")
        
        # Update status using service
        result = await candidate_interview_service.update_interview_status(
            interview_id, status, user_id
        )
        
        return result
        
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        elif "not authorized" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e)
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
    except Exception as e:
        logger.error("Failed to update interview status", interview_id=interview_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update interview status"
        )


@router.get("/user/{user_id}/interviews", response_model=List[CandidateInterviewRead])
async def get_user_interviews(
    user_id: str,
    status: CandidateInterviewStatus = None,
    current_user=Depends(validate_request)
):
    """Get interviews for a specific user (admin or self)"""
    try:
        current_user_id = current_user.get("user_id")
        
        # Check if user is requesting their own interviews or is admin
        if current_user_id != user_id:
            # TODO: Add admin role check here
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access other user interviews"
            )
        
        if status:
            interviews = await candidate_interview_service.get_interviews_by_status(user_id, status)
        else:
            interviews = await candidate_interview_service.get_user_interviews(user_id)
        
        return interviews
        
    except Exception as e:
        logger.error("Failed to get user interviews", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user interviews"
        )


@router.delete("/{interview_id}")
async def delete_candidate_interview(
    interview_id: str,
    current_user=Depends(validate_request)
):
    """Delete a candidate interview"""
    try:
        user_id = current_user.get("user_id")
        
        # Delete the interview using service
        result = await candidate_interview_service.delete_candidate_interview(interview_id, user_id)
        
        return result
        
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        elif "not authorized" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e)
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
    except Exception as e:
        logger.error("Failed to delete candidate interview", interview_id=interview_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete candidate interview"
        )
