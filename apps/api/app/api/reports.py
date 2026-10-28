import io
import csv
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    BackupSource, BackupArtifact, VerificationJob,
    RecoveryTest, Notification, User
)
from app.schemas import DashboardSummary, VerificationJobResponse, NotificationResponse
from app.security import get_current_user

router = APIRouter(prefix="/reports", tags=["Reports & Analytics"])

@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    sources = db.query(BackupSource).all()
    total_sources = len(sources)
    healthy_sources = sum(1 for s in sources if s.last_verified_at and (not s.last_failed_at or s.last_verified_at >= s.last_failed_at))
    failed_sources = sum(1 for s in sources if s.last_failed_at and (not s.last_verified_at or s.last_failed_at > s.last_verified_at))
    warning_sources = total_sources - (healthy_sources + failed_sources)

    total_artifacts = db.query(BackupArtifact).count()
    total_jobs = db.query(VerificationJob).count()

    # Recovery test metrics
    recovery_tests = db.query(RecoveryTest).all()
    rec_count = len(recovery_tests)
    rec_passed = sum(1 for r in recovery_tests if r.status == "passed")
    recovery_rate = (rec_passed / rec_count * 100.0) if rec_count > 0 else 100.0

    # RTO compliance metrics
    rto_met_count = sum(1 for r in recovery_tests if r.rto_met is True)
    rto_rate = (rto_met_count / rec_count * 100.0) if rec_count > 0 else 100.0

    recent_jobs = db.query(VerificationJob).order_by(VerificationJob.created_at.desc()).limit(10).all()
    recent_notifs = db.query(Notification).order_by(Notification.created_at.desc()).limit(10).all()

    return {
        "total_sources": total_sources,
        "healthy_sources": healthy_sources,
        "warning_sources": max(0, warning_sources),
        "failed_sources": failed_sources,
        "total_artifacts": total_artifacts,
        "total_jobs": total_jobs,
        "recovery_test_success_rate": round(recovery_rate, 1),
        "rto_compliance_rate": round(rto_rate, 1),
        "recent_jobs": recent_jobs,
        "recent_notifications": recent_notifs
    }

@router.get("/export/csv")
def export_verification_jobs_csv(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    jobs = db.query(VerificationJob).order_by(VerificationJob.created_at.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow([
        "Job ID", "Artifact File", "Job Type", "Status",
        "Duration (ms)", "Error Summary", "Created At", "Completed At"
    ])
    
    for job in jobs:
        file_name = job.artifact.file_name if job.artifact else "N/A"
        writer.writerow([
            job.id,
            file_name,
            job.job_type,
            job.status,
            job.duration_ms,
            job.error_summary or "",
            job.created_at.isoformat() if job.created_at else "",
            job.completed_at.isoformat() if job.completed_at else ""
        ])
        
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=backup_verification_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"}
    )
