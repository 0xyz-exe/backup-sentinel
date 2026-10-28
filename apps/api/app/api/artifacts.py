from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import uuid

from app.database import get_db
from app.models import (
    BackupArtifact, BackupSource, VerificationJob,
    VerificationPolicy, User
)
from app.schemas import (
    BackupArtifactResponse, VerificationJobResponse, VerificationJobTrigger
)
from app.security import get_current_user, require_role
from app.verification.engine import run_verification_pipeline
from app.adapters.local_fs import LocalFilesystemAdapter
from app.services.audit_service import record_audit_log

router = APIRouter(prefix="/artifacts", tags=["Backup Artifacts"])

@router.get("", response_model=List[BackupArtifactResponse])
def list_artifacts(
    source_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(BackupArtifact)
    if source_id:
        query = query.filter(BackupArtifact.source_id == source_id)
    return query.order_by(BackupArtifact.discovered_at.desc()).all()

@router.get("/{artifact_id}", response_model=BackupArtifactResponse)
def get_artifact(artifact_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    artifact = db.query(BackupArtifact).filter(BackupArtifact.id == artifact_id).first()
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return artifact

@router.post("/{artifact_id}/verify", response_model=VerificationJobResponse)
def trigger_artifact_verification(
    artifact_id: str,
    trigger_in: VerificationJobTrigger,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "operator"]))
):
    artifact = db.query(BackupArtifact).filter(BackupArtifact.id == artifact_id).first()
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    # Idempotency check: prevent duplicate simultaneous verification jobs
    if trigger_in.idempotency_key:
        existing_job = db.query(VerificationJob).filter(
            VerificationJob.idempotency_key == trigger_in.idempotency_key
        ).first()
        if existing_job:
            return existing_job

    policy = None
    if trigger_in.policy_id:
        policy = db.query(VerificationPolicy).filter(VerificationPolicy.id == trigger_in.policy_id).first()

    # Create Job record
    job_id = f"job_{uuid.uuid4().hex[:12]}"
    job = VerificationJob(
        id=job_id,
        artifact_id=artifact.id,
        policy_id=policy.id if policy else None,
        job_type=trigger_in.job_type,
        status="pending",
        idempotency_key=trigger_in.idempotency_key
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Resolve local path for verification execution
    source = artifact.source
    if source.source_type == "local_fs":
        adapter = LocalFilesystemAdapter(source.config)
        local_path = adapter.get_local_path(artifact.artifact_key)
    else:
        raise HTTPException(status_code=400, detail="Only local filesystem source is verified directly in current runtime")

    # Run Verification Pipeline
    job = run_verification_pipeline(
        db=db,
        job=job,
        local_file_path=local_path,
        policy=policy,
        expected_checksum=trigger_in.expected_checksum
    )

    record_audit_log(
        db=db,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="trigger_verification",
        resource_type="verification_job",
        resource_id=job.id,
        metadata={"artifact_id": artifact.id, "status": job.status}
    )

    db.refresh(job)
    return job
