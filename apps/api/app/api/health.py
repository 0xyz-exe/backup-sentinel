from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.config import settings

router = APIRouter(prefix="/health", tags=["System Health"])

@router.get("/live")
def liveness():
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}

@router.get("/ready")
def readiness(db: Session = Depends(get_db)):
    db_ok = False
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
        
    return {
        "status": "ready" if db_ok else "unhealthy",
        "database": "connected" if db_ok else "disconnected",
        "environment": settings.ENVIRONMENT
    }

@router.get("/workers")
def worker_status():
    return {
        "worker_engine": "embedded_async_scheduler",
        "status": "healthy",
        "docker_sandbox_enabled": settings.ENABLE_DOCKER_RECOVERY
    }
