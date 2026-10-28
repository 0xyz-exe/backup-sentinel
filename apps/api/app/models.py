import datetime
import json
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(32), default="viewer", nullable=False)  # admin, operator, auditor, viewer
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)


class BackupSource(Base):
    __tablename__ = "backup_sources"
    
    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    source_type = Column(String(32), nullable=False)  # local_fs, s3, sftp
    config = Column(JSON, nullable=False)  # root_path, bucket, endpoint, prefix, etc.
    enabled = Column(Boolean, default=True, nullable=False)
    last_verified_at = Column(DateTime, nullable=True)
    last_failed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)
    
    artifacts = relationship("BackupArtifact", back_populates="source", cascade="all, delete-orphan")


class BackupArtifact(Base):
    __tablename__ = "backup_artifacts"
    
    id = Column(String(36), primary_key=True)
    source_id = Column(String(36), ForeignKey("backup_sources.id"), nullable=False)
    artifact_key = Column(String(1024), nullable=False)  # safe relative path or s3 key
    file_name = Column(String(255), nullable=False)
    format = Column(String(32), nullable=False)  # zip, tar, pg_custom, sql_pg, sql_mysql, unknown
    size_bytes = Column(Integer, nullable=False)
    source_version = Column(String(64), nullable=True)
    sha256_checksum = Column(String(64), nullable=True)
    expected_checksum = Column(String(64), nullable=True)
    discovered_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    modified_at = Column(DateTime, nullable=True)
    metadata_json = Column(JSON, default=dict)
    
    source = relationship("BackupSource", back_populates="artifacts")
    jobs = relationship("VerificationJob", back_populates="artifact", cascade="all, delete-orphan")


class VerificationPolicy(Base):
    __tablename__ = "verification_policies"
    
    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    config = Column(JSON, default=dict)  # enabled_checks, notify_on_fail, etc.
    rto_target_seconds = Column(Integer, default=300)  # default 5 minutes
    rpo_target_seconds = Column(Integer, default=86400)  # default 24 hours
    schedule_cron = Column(String(64), nullable=True)
    enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)
    
    jobs = relationship("VerificationJob", back_populates="policy")


class VerificationJob(Base):
    __tablename__ = "verification_jobs"
    
    id = Column(String(36), primary_key=True)
    artifact_id = Column(String(36), ForeignKey("backup_artifacts.id"), nullable=False)
    policy_id = Column(String(36), ForeignKey("verification_policies.id"), nullable=True)
    job_type = Column(String(32), default="full", nullable=False)  # integrity, structural, recovery_test, full
    status = Column(String(32), default="pending", nullable=False)  # pending, running, verified, verified_with_warnings, failed, inconclusive
    current_stage = Column(String(64), default="discovery")
    progress = Column(Integer, default=0)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, default=0)
    error_summary = Column(Text, nullable=True)
    idempotency_key = Column(String(128), unique=True, index=True, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    
    artifact = relationship("BackupArtifact", back_populates="jobs")
    policy = relationship("VerificationPolicy", back_populates="jobs")
    results = relationship("VerificationResult", back_populates="job", cascade="all, delete-orphan")
    recovery_tests = relationship("RecoveryTest", back_populates="job", cascade="all, delete-orphan")


class VerificationResult(Base):
    __tablename__ = "verification_results"
    
    id = Column(String(36), primary_key=True)
    job_id = Column(String(36), ForeignKey("verification_jobs.id"), nullable=False)
    stage = Column(String(64), nullable=False)  # accessibility, cryptographic, structural, database, policy
    check_name = Column(String(128), nullable=False)
    status = Column(String(32), nullable=False)  # pass, fail, warn, skipped
    expected_value = Column(Text, nullable=True)
    actual_value = Column(Text, nullable=True)
    duration_ms = Column(Integer, default=0)
    evidence_json = Column(JSON, default=dict)
    error_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    
    job = relationship("VerificationJob", back_populates="results")


class RecoveryTest(Base):
    __tablename__ = "recovery_tests"
    
    id = Column(String(36), primary_key=True)
    verification_job_id = Column(String(36), ForeignKey("verification_jobs.id"), nullable=False)
    artifact_id = Column(String(36), ForeignKey("backup_artifacts.id"), nullable=False)
    recovery_profile = Column(String(64), nullable=False)  # generic_archive, postgres_disposable, mysql_disposable
    environment_type = Column(String(64), nullable=False)  # sandbox_filesystem, disposable_container
    restore_duration_ms = Column(Integer, default=0)
    assertions_passed = Column(Integer, default=0)
    assertions_failed = Column(Integer, default=0)
    cleanup_status = Column(String(32), default="pending")  # pending, cleaned, failed
    rto_target_seconds = Column(Integer, default=300)
    rto_met = Column(Boolean, nullable=True)
    status = Column(String(32), default="pending")  # passed, failed, timeout
    diagnostics = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    
    job = relationship("VerificationJob", back_populates="recovery_tests")


class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(String(36), primary_key=True)
    event_type = Column(String(64), nullable=False)
    severity = Column(String(32), default="info")  # info, warning, critical
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    channel = Column(String(32), default="in_app")  # in_app, webhook, email
    delivery_status = Column(String(32), default="sent")  # sent, failed, pending
    attempts = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    delivered_at = Column(DateTime, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(String(36), primary_key=True)
    actor_id = Column(String(36), nullable=True)
    actor_email = Column(String(255), nullable=True)
    action = Column(String(128), nullable=False)
    resource_type = Column(String(64), nullable=False)
    resource_id = Column(String(128), nullable=True)
    metadata_json = Column(JSON, default=dict)
    previous_hash = Column(String(64), nullable=True)
    event_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
