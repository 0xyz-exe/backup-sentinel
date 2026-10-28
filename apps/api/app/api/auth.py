from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import uuid

from app.database import get_db
from app.models import User
from app.schemas import Token, UserResponse, UserCreate
from app.security import (
    verify_password, get_password_hash, create_access_token,
    get_current_user, require_role
)
from app.services.audit_service import record_audit_log

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user account")
        
    access_token = create_access_token(
        data={"sub": user.id, "email": user.email, "role": user.role}
    )
    
    record_audit_log(
        db=db,
        actor_id=user.id,
        actor_email=user.email,
        action="user_login",
        resource_type="auth",
        resource_id=user.id
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role,
        "email": user.email
    }

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/users", response_model=UserResponse, dependencies=[Depends(require_role(["admin"]))])
def create_user(user_in: UserCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="User email already registered")
        
    new_user = User(
        id=f"usr_{uuid.uuid4().hex[:12]}",
        email=user_in.email,
        password_hash=get_password_hash(user_in.password),
        role=user_in.role,
        is_active=user_in.is_active
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    record_audit_log(
        db=db,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="create_user",
        resource_type="user",
        resource_id=new_user.id,
        metadata={"email": new_user.email, "role": new_user.role}
    )
    return new_user
