from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_async_session
from app.core.security import validate_request
from app.services.candidate_interview_planner_service import candidate_interview_planner_service
from app.models.candidate_interview_planner import (
    CandidateInterviewPlanner, 
    CandidateInterviewPlannerCreate, 
    CandidateInterviewPlannerRead, 
    CandidateInterviewPlannerUpdate
)
from typing import List
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/interview-planners", tags=["Interview Planners"])


@router.post("/", response_model=CandidateInterviewPlannerRead)
async def create_interview_planner(
    planner: CandidateInterviewPlannerCreate,
    current_user=Depends(validate_request)
):
    """Create a new interview planner entry"""
    try:
        user_id = current_user.get("user_id")
        
        # Create the planner using service
        planner_data = planner.dict()
        created_planner = await candidate_interview_planner_service.create_interview_planner(planner_data, user_id)
        
        return created_planner
        
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
        logger.error("Failed to create interview planner", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create interview planner"
        )


@router.get("/interview/{interview_id}", response_model=List[CandidateInterviewPlannerRead])
async def get_interview_plan(
    interview_id: str,
    current_user=Depends(validate_request)
):
    """Get the complete interview plan for a candidate interview"""
    try:
        user_id = current_user.get("user_id")
        
        # Get the interview plan using service
        plan = await candidate_interview_planner_service.get_interview_plan(interview_id, user_id)
        
        return plan
        
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
        logger.error("Failed to get interview plan", interview_id=interview_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get interview plan"
        )


@router.get("/{planner_id}", response_model=CandidateInterviewPlannerRead)
async def get_interview_planner(
    planner_id: str,
    db: AsyncSession = Depends(get_async_session),
    current_user=Depends(validate_request)
):
    """Get a specific interview planner by ID"""
    try:
        user_id = current_user.get("user_id")
        
        planner = await candidate_interview_planner_dao.get_by_id(db, planner_id)
        if not planner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview planner not found"
            )
        
        # Verify ownership through the candidate interview
        candidate_interview = await candidate_interview_dao.get_by_id(db, planner.candidateInterviewId)
        if candidate_interview.userId != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this planner"
            )
        
        return CandidateInterviewPlannerRead.from_orm(planner)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get interview planner", planner_id=planner_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get interview planner"
        )


@router.put("/{planner_id}", response_model=CandidateInterviewPlannerRead)
async def update_interview_planner(
    planner_id: str,
    planner_update: CandidateInterviewPlannerUpdate,
    db: AsyncSession = Depends(get_async_session),
    current_user=Depends(validate_request)
):
    """Update an interview planner"""
    try:
        user_id = current_user.get("user_id")
        
        # Get existing planner
        existing_planner = await candidate_interview_planner_dao.get_by_id(db, planner_id)
        if not existing_planner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview planner not found"
            )
        
        # Verify ownership through the candidate interview
        candidate_interview = await candidate_interview_dao.get_by_id(db, existing_planner.candidateInterviewId)
        if candidate_interview.userId != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this planner"
            )
        
        # Update the planner
        update_data = planner_update.dict(exclude_unset=True)
        updated_planner = await candidate_interview_planner_dao.update(
            db, db_obj=existing_planner, obj_in=update_data
        )
        
        logger.info("Updated interview planner", planner_id=planner_id, user_id=user_id)
        return CandidateInterviewPlannerRead.from_orm(updated_planner)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update interview planner", planner_id=planner_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update interview planner"
        )


@router.patch("/{planner_id}/instructions")
async def update_planner_instructions(
    planner_id: str,
    instructions: str,
    db: AsyncSession = Depends(get_async_session),
    current_user=Depends(validate_request)
):
    """Update the interview instructions for a specific planner"""
    try:
        user_id = current_user.get("user_id")
        
        # Get existing planner
        existing_planner = await candidate_interview_planner_dao.get_by_id(db, planner_id)
        if not existing_planner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview planner not found"
            )
        
        # Verify ownership through the candidate interview
        candidate_interview = await candidate_interview_dao.get_by_id(db, existing_planner.candidateInterviewId)
        if candidate_interview.userId != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this planner"
            )
        
        # Update instructions
        updated_planner = await candidate_interview_planner_dao.update_interview_instructions(
            db, planner_id, instructions
        )
        
        logger.info("Updated planner instructions", planner_id=planner_id, user_id=user_id)
        return {"message": "Instructions updated successfully", "instructions": instructions}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update planner instructions", planner_id=planner_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update planner instructions"
        )


@router.get("/{planner_id}/next")
async def get_next_planner_in_sequence(
    planner_id: str,
    db: AsyncSession = Depends(get_async_session),
    current_user=Depends(validate_request)
):
    """Get the next planner in the interview sequence"""
    try:
        user_id = current_user.get("user_id")
        
        # Get current planner
        current_planner = await candidate_interview_planner_dao.get_by_id(db, planner_id)
        if not current_planner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview planner not found"
            )
        
        # Verify ownership through the candidate interview
        candidate_interview = await candidate_interview_dao.get_by_id(db, current_planner.candidateInterviewId)
        if candidate_interview.userId != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this planner"
            )
        
        # Get next planner
        next_planner = await candidate_interview_planner_dao.get_next_planner_in_sequence(
            db, current_planner.candidateInterviewId, planner_id
        )
        
        if next_planner:
            return CandidateInterviewPlannerRead.from_orm(next_planner)
        else:
            return {"message": "No more steps in the interview sequence"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get next planner", planner_id=planner_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get next planner"
        )


@router.delete("/{planner_id}")
async def delete_interview_planner(
    planner_id: str,
    db: AsyncSession = Depends(get_async_session),
    current_user=Depends(validate_request)
):
    """Delete an interview planner"""
    try:
        user_id = current_user.get("user_id")
        
        # Get existing planner
        existing_planner = await candidate_interview_planner_dao.get_by_id(db, planner_id)
        if not existing_planner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview planner not found"
            )
        
        # Verify ownership through the candidate interview
        candidate_interview = await candidate_interview_dao.get_by_id(db, existing_planner.candidateInterviewId)
        if candidate_interview.userId != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this planner"
            )
        
        # Delete the planner
        await candidate_interview_planner_dao.delete(db, id=planner_id)
        
        logger.info("Deleted interview planner", planner_id=planner_id, user_id=user_id)
        return {"message": "Interview planner deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete interview planner", planner_id=planner_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete interview planner"
        )


@router.delete("/interview/{interview_id}/plan")
async def delete_interview_plan(
    interview_id: str,
    db: AsyncSession = Depends(get_async_session),
    current_user=Depends(validate_request)
):
    """Delete the entire interview plan for a candidate interview"""
    try:
        user_id = current_user.get("user_id")
        
        # Verify the candidate interview exists and belongs to the user
        candidate_interview = await candidate_interview_dao.get_by_id(db, interview_id)
        if not candidate_interview:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate interview not found"
            )
        
        if candidate_interview.userId != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this interview plan"
            )
        
        # Delete the entire plan
        await candidate_interview_planner_dao.delete_interview_plan(db, interview_id)
        
        logger.info("Deleted interview plan", interview_id=interview_id, user_id=user_id)
        return {"message": "Interview plan deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete interview plan", interview_id=interview_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete interview plan"
        )
