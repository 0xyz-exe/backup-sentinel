from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base
from app.api import (
    auth, sources, artifacts, jobs, policies,
    recovery, reports, health, audit
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database schema tables exist
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Automated Backup Verification & Recovery Testing Platform",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers under /api/v1
app.include_router(auth.router, prefix="/api/v1")
app.include_router(sources.router, prefix="/api/v1")
app.include_router(artifacts.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1")
app.include_router(policies.router, prefix="/api/v1")
app.include_router(recovery.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")
app.include_router(health.router, prefix="/api/v1")
app.include_router(audit.router, prefix="/api/v1")

@app.get("/")
def root():
    return {
        "platform": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "api_v1": "/api/v1"
    }
