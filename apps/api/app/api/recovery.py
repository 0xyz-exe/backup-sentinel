from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import RecoveryTest, User
from app.schemas import RecoveryTestResponse
from app.security import get_current_user

router = APIRouter(prefix="/recovery-tests", tags=["Recovery Testing"])

@router.get("", response_model=List[RecoveryTestResponse])
def list_recovery_tests(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(RecoveryTest).order_by(RecoveryTest.created_at.desc()).limit(limit).all()

@router.get("/{test_id}", response_model=RecoveryTestResponse)
def get_recovery_test(test_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    test = db.query(RecoveryTest).filter(RecoveryTest.id == test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Recovery test record not found")
    return test
