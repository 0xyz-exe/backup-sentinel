from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import uuid

from app.database import get_db
from app.models import VerificationPolicy, User
from app.schemas import (
    VerificationPolicyCreate, VerificationPolicyUpdate, VerificationPolicyResponse
)
from app.security import get_current_user, require_role

router = APIRouter(prefix="/policies", tags=["Verification Policies"])

@router.get("", response_model=List[VerificationPolicyResponse])
def list_policies(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(VerificationPolicy).order_by(VerificationPolicy.created_at.desc()).all()

@router.post("", response_model=VerificationPolicyResponse, dependencies=[Depends(require_role(["admin"]))])
def create_policy(
    policy_in: VerificationPolicyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    new_policy = VerificationPolicy(
        id=f"pol_{uuid.uuid4().hex[:12]}",
        name=policy_in.name,
        description=policy_in.description,
        config=policy_in.config,
        rto_target_seconds=policy_in.rto_target_seconds,
        rpo_target_seconds=policy_in.rpo_target_seconds,
        schedule_cron=policy_in.schedule_cron,
        enabled=policy_in.enabled
    )
    db.add(new_policy)
    db.commit()
    db.refresh(new_policy)
    return new_policy

@router.get("/{policy_id}", response_model=VerificationPolicyResponse)
def get_policy(policy_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    policy = db.query(VerificationPolicy).filter(VerificationPolicy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy

@router.patch("/{policy_id}", response_model=VerificationPolicyResponse, dependencies=[Depends(require_role(["admin"]))])
def update_policy(
    policy_id: str,
    update_in: VerificationPolicyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    policy = db.query(VerificationPolicy).filter(VerificationPolicy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    if update_in.name is not None:
        policy.name = update_in.name
    if update_in.description is not None:
        policy.description = update_in.description
    if update_in.config is not None:
        policy.config = update_in.config
    if update_in.rto_target_seconds is not None:
        policy.rto_target_seconds = update_in.rto_target_seconds
    if update_in.rpo_target_seconds is not None:
        policy.rpo_target_seconds = update_in.rpo_target_seconds
    if update_in.schedule_cron is not None:
        policy.schedule_cron = update_in.schedule_cron
    if update_in.enabled is not None:
        policy.enabled = update_in.enabled

    db.commit()
    db.refresh(policy)
    return policy

@router.delete("/{policy_id}", dependencies=[Depends(require_role(["admin"]))])
def delete_policy(policy_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    policy = db.query(VerificationPolicy).filter(VerificationPolicy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    db.delete(policy)
    db.commit()
    return {"message": "Policy deleted successfully"}
