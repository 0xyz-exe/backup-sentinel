from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AuditLog, User
from app.schemas import AuditLogResponse
from app.security import require_role
from app.services.audit_service import verify_audit_chain_integrity

router = APIRouter(prefix="/audit", tags=["Audit Logs"])

@router.get("", response_model=List[AuditLogResponse], dependencies=[Depends(require_role(["admin", "auditor"]))])
def list_audit_logs(limit: int = 100, db: Session = Depends(get_db)):
    return db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()

@router.get("/verify-chain", dependencies=[Depends(require_role(["admin", "auditor"]))])
def verify_chain(db: Session = Depends(get_db)):
    return verify_audit_chain_integrity(db)
