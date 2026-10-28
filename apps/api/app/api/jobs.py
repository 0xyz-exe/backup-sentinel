from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.models import VerificationJob, User
from app.schemas import VerificationJobResponse
from app.security import get_current_user, require_role

router = APIRouter(prefix="/jobs", tags=["Verification Jobs"])

@router.get("", response_model=List[VerificationJobResponse])
def list_jobs(
    status_filter: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(VerificationJob)
    if status_filter:
        query = query.filter(VerificationJob.status == status_filter)
    return query.order_by(VerificationJob.created_at.desc()).limit(limit).all()

@router.get("/{job_id}", response_model=VerificationJobResponse)
def get_job(job_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    job = db.query(VerificationJob).filter(VerificationJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Verification job not found")
    return job

@router.post("/{job_id}/cancel", response_model=VerificationJobResponse, dependencies=[Depends(require_role(["admin", "operator"]))])
def cancel_job(job_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    job = db.query(VerificationJob).filter(VerificationJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Verification job not found")
    if job.status in ["verified", "verified_with_warnings", "failed"]:
        raise HTTPException(status_code=400, detail="Completed jobs cannot be cancelled")
        
    job.status = "cancelled"
    job.completed_at = datetime.utcnow()
    job.error_summary = "Verification was cancelled by operator request."
    db.commit()
    db.refresh(job)
    return job
