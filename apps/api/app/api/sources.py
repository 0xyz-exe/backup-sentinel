from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import uuid

from app.database import get_db
from app.models import BackupSource, BackupArtifact, User
from app.schemas import (
    BackupSourceCreate, BackupSourceUpdate, BackupSourceResponse,
    BackupArtifactResponse
)
from app.security import get_current_user, require_role
from app.adapters.local_fs import LocalFilesystemAdapter
from app.adapters.s3 import S3StorageAdapter
from app.services.audit_service import record_audit_log

router = APIRouter(prefix="/sources", tags=["Backup Sources"])

def get_adapter_for_source(source: BackupSource):
    if source.source_type == "local_fs":
        return LocalFilesystemAdapter(source.config)
    elif source.source_type == "s3":
        return S3StorageAdapter(source.config)
    else:
        raise ValueError(f"Unsupported source type: {source.source_type}")

@router.get("", response_model=List[BackupSourceResponse])
def list_sources(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(BackupSource).order_by(BackupSource.created_at.desc()).all()

@router.post("", response_model=BackupSourceResponse, dependencies=[Depends(require_role(["admin", "operator"]))])
def create_source(
    source_in: BackupSourceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Validate adapter config before persisting
    if source_in.source_type == "local_fs":
        adapter = LocalFilesystemAdapter(source_in.config)
        ok, msg = adapter.test_connection()
        if not ok:
            raise HTTPException(status_code=400, detail=f"Configuration test failed: {msg}")

    new_source = BackupSource(
        id=f"src_{uuid.uuid4().hex[:12]}",
        name=source_in.name,
        description=source_in.description,
        source_type=source_in.source_type,
        config=source_in.config,
        enabled=source_in.enabled
    )
    db.add(new_source)
    db.commit()
    db.refresh(new_source)

    record_audit_log(
        db=db,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="create_backup_source",
        resource_type="backup_source",
        resource_id=new_source.id,
        metadata={"name": new_source.name, "type": new_source.source_type}
    )
    return new_source

@router.get("/{source_id}", response_model=BackupSourceResponse)
def get_source(source_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    source = db.query(BackupSource).filter(BackupSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Backup source not found")
    return source

@router.patch("/{source_id}", response_model=BackupSourceResponse, dependencies=[Depends(require_role(["admin", "operator"]))])
def update_source(
    source_id: str,
    update_in: BackupSourceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    source = db.query(BackupSource).filter(BackupSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Backup source not found")

    if update_in.name is not None:
        source.name = update_in.name
    if update_in.description is not None:
        source.description = update_in.description
    if update_in.config is not None:
        source.config = update_in.config
    if update_in.enabled is not None:
        source.enabled = update_in.enabled

    db.commit()
    db.refresh(source)
    return source

@router.post("/{source_id}/test-connection")
def test_source_connection(
    source_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    source = db.query(BackupSource).filter(BackupSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Backup source not found")

    try:
        adapter = get_adapter_for_source(source)
        success, message = adapter.test_connection()
        return {"success": success, "message": message}
    except Exception as e:
        return {"success": False, "message": str(e)}

@router.post("/{source_id}/discover", response_model=List[BackupArtifactResponse])
def discover_artifacts(
    source_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "operator"]))
):
    source = db.query(BackupSource).filter(BackupSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Backup source not found")

    adapter = get_adapter_for_source(source)
    discovered = adapter.discover_artifacts()
    persisted_artifacts = []

    for item in discovered:
        # Check if already tracked
        existing = db.query(BackupArtifact).filter(
            BackupArtifact.source_id == source.id,
            BackupArtifact.artifact_key == item.artifact_key
        ).first()

        if existing:
            existing.size_bytes = item.size_bytes
            existing.modified_at = item.modified_at
            existing.metadata_json = item.metadata
            persisted_artifacts.append(existing)
        else:
            new_artifact = BackupArtifact(
                id=f"art_{uuid.uuid4().hex[:12]}",
                source_id=source.id,
                artifact_key=item.artifact_key,
                file_name=item.file_name,
                format=item.format,
                size_bytes=item.size_bytes,
                modified_at=item.modified_at,
                metadata_json=item.metadata
            )
            db.add(new_artifact)
            persisted_artifacts.append(new_artifact)

    db.commit()
    for a in persisted_artifacts:
        db.refresh(a)

    record_audit_log(
        db=db,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="discover_artifacts",
        resource_type="backup_source",
        resource_id=source.id,
        metadata={"discovered_count": len(persisted_artifacts)}
    )
    return persisted_artifacts
