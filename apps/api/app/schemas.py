from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

# Auth schemas
class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    email: str

class TokenData(BaseModel):
    user_id: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None

class UserBase(BaseModel):
    email: str
    role: str = "viewer"
    is_active: bool = True

class UserCreate(BaseModel):
    email: str
    password: str = Field(min_length=8)
    role: str = "viewer"

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(UserBase):
    id: str
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True

# Backup Source schemas
class BackupSourceBase(BaseModel):
    name: str
    description: Optional[str] = None
    source_type: str  # local_fs, s3, sftp
    config: Dict[str, Any]
    enabled: bool = True

class BackupSourceCreate(BackupSourceBase):
    pass

class BackupSourceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None

class BackupSourceResponse(BackupSourceBase):
    id: str
    last_verified_at: Optional[datetime] = None
    last_failed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True

# Backup Artifact schemas
class BackupArtifactResponse(BaseModel):
    id: str
    source_id: str
    artifact_key: str
    file_name: str
    format: str
    size_bytes: int
    source_version: Optional[str] = None
    sha256_checksum: Optional[str] = None
    expected_checksum: Optional[str] = None
    discovered_at: datetime
    modified_at: Optional[datetime] = None
    metadata_json: Dict[str, Any]
    class Config:
        from_attributes = True

# Policy schemas
class VerificationPolicyBase(BaseModel):
    name: str
    description: Optional[str] = None
    config: Dict[str, Any] = Field(default_factory=dict)
    rto_target_seconds: int = 300
    rpo_target_seconds: int = 86400
    schedule_cron: Optional[str] = None
    enabled: bool = True

class VerificationPolicyCreate(VerificationPolicyBase):
    pass

class VerificationPolicyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    rto_target_seconds: Optional[int] = None
    rpo_target_seconds: Optional[int] = None
    schedule_cron: Optional[str] = None
    enabled: Optional[bool] = None

class VerificationPolicyResponse(VerificationPolicyBase):
    id: str
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True

# Verification Result schemas
class VerificationResultResponse(BaseModel):
    id: str
    job_id: str
    stage: str
    check_name: str
    status: str
    expected_value: Optional[str] = None
    actual_value: Optional[str] = None
    duration_ms: int
    evidence_json: Dict[str, Any]
    error_summary: Optional[str] = None
    created_at: datetime
    class Config:
        from_attributes = True

# Recovery Test schemas
class RecoveryTestResponse(BaseModel):
    id: str
    verification_job_id: str
    artifact_id: str
    recovery_profile: str
    environment_type: str
    restore_duration_ms: int
    assertions_passed: int
    assertions_failed: int
    cleanup_status: str
    rto_target_seconds: int
    rto_met: Optional[bool] = None
    status: str
    diagnostics: Dict[str, Any]
    created_at: datetime
    class Config:
        from_attributes = True

# Verification Job schemas
class VerificationJobResponse(BaseModel):
    id: str
    artifact_id: str
    policy_id: Optional[str] = None
    job_type: str
    status: str
    current_stage: str
    progress: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: int
    error_summary: Optional[str] = None
    idempotency_key: Optional[str] = None
    created_at: datetime
    results: List[VerificationResultResponse] = []
    recovery_tests: List[RecoveryTestResponse] = []
    class Config:
        from_attributes = True

class VerificationJobTrigger(BaseModel):
    policy_id: Optional[str] = None
    job_type: str = "full"
    expected_checksum: Optional[str] = None
    idempotency_key: Optional[str] = None

# Notification schemas
class NotificationResponse(BaseModel):
    id: str
    event_type: str
    severity: str
    title: str
    message: str
    channel: str
    delivery_status: str
    attempts: int
    created_at: datetime
    delivered_at: Optional[datetime] = None
    class Config:
        from_attributes = True

# Audit Log schemas
class AuditLogResponse(BaseModel):
    id: str
    actor_id: Optional[str] = None
    actor_email: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    metadata_json: Dict[str, Any]
    previous_hash: Optional[str] = None
    event_hash: str
    created_at: datetime
    class Config:
        from_attributes = True

# Dashboard Summary schemas
class DashboardSummary(BaseModel):
    total_sources: int
    healthy_sources: int
    warning_sources: int
    failed_sources: int
    total_artifacts: int
    total_jobs: int
    recovery_test_success_rate: float
    rto_compliance_rate: float
    recent_jobs: List[VerificationJobResponse]
    recent_notifications: List[NotificationResponse]
