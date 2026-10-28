import time
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models import (
    BackupArtifact, VerificationJob, VerificationResult,
    VerificationPolicy, RecoveryTest
)
from app.verification.checksum import calculate_sha256_stream
from app.verification.archive import verify_zip_archive, verify_tar_archive
from app.verification.postgres import verify_postgres_custom_dump
from app.verification.sql import verify_sql_dump
from app.recovery.orchestrator import run_recovery_test_orchestrator
from app.services.audit_service import record_audit_log

def run_verification_pipeline(
    db: Session,
    job: VerificationJob,
    local_file_path: str,
    policy: Optional[VerificationPolicy] = None,
    expected_checksum: Optional[str] = None
) -> VerificationJob:
    job_start = time.time()
    job.started_at = datetime.utcnow()
    job.status = "running"
    db.commit()
    
    artifact = job.artifact
    has_critical_failure = False
    has_warnings = False
    
    try:
        # STAGE 1 & 2: ACCESSIBILITY & SIZE VALIDATION
        job.current_stage = "accessibility"
        job.progress = 15
        db.commit()
        
        t0 = time.time()
        import os
        if not os.path.exists(local_file_path):
            res = VerificationResult(
                id=f"res_{job.id}_access",
                job_id=job.id,
                stage="accessibility",
                check_name="file_readable",
                status="fail",
                actual_value="File does not exist or access denied",
                duration_ms=int((time.time() - t0) * 1000),
                evidence_json={"path": local_file_path},
                error_summary="Backup artifact file could not be accessed."
            )
            db.add(res)
            job.status = "failed"
            job.error_summary = "Accessibility verification failed: artifact not found"
            job.completed_at = datetime.utcnow()
            job.duration_ms = int((time.time() - job_start) * 1000)
            db.commit()
            return job
            
        file_size = os.path.getsize(local_file_path)
        if file_size == 0:
            res = VerificationResult(
                id=f"res_{job.id}_access",
                job_id=job.id,
                stage="accessibility",
                check_name="non_zero_size",
                status="fail",
                actual_value="0 bytes",
                duration_ms=int((time.time() - t0) * 1000),
                evidence_json={"size_bytes": 0},
                error_summary="Backup artifact is an empty 0-byte file."
            )
            db.add(res)
            job.status = "failed"
            job.error_summary = "Accessibility verification failed: artifact is 0 bytes"
            job.completed_at = datetime.utcnow()
            job.duration_ms = int((time.time() - job_start) * 1000)
            db.commit()
            return job
            
        res_access = VerificationResult(
            id=f"res_{job.id}_access",
            job_id=job.id,
            stage="accessibility",
            check_name="file_accessibility",
            status="pass",
            actual_value=f"{file_size} bytes",
            duration_ms=int((time.time() - t0) * 1000),
            evidence_json={"size_bytes": file_size, "accessible": True}
        )
        db.add(res_access)
        db.commit()

        # STAGE 3: CRYPTOGRAPHIC INTEGRITY
        job.current_stage = "cryptographic"
        job.progress = 35
        db.commit()
        
        with open(local_file_path, "rb") as f:
            checksum_res = calculate_sha256_stream(f, expected_checksum or artifact.expected_checksum)
            
        artifact.sha256_checksum = checksum_res["computed_checksum"]
        res_crypto = VerificationResult(
            id=f"res_{job.id}_crypto",
            job_id=job.id,
            stage="cryptographic",
            check_name="sha256_checksum",
            status=checksum_res["status"],
            expected_value=checksum_res["expected_checksum"],
            actual_value=checksum_res["computed_checksum"],
            duration_ms=checksum_res["duration_ms"],
            evidence_json=checksum_res,
            error_summary=checksum_res["summary"] if checksum_res["status"] == "fail" else None
        )
        db.add(res_crypto)
        if checksum_res["status"] == "fail":
            has_critical_failure = True
        elif checksum_res["expected_checksum"] is None:
            has_warnings = True  # Reference checksum unconfirmed
        db.commit()

        # STAGE 4: STRUCTURAL VALIDATION
        job.current_stage = "structural"
        job.progress = 60
        db.commit()
        
        fmt = artifact.format.lower()
        struct_res = None
        if fmt == "zip":
            struct_res = verify_zip_archive(local_file_path)
        elif fmt == "tar":
            struct_res = verify_tar_archive(local_file_path)
        elif fmt == "pg_custom":
            struct_res = verify_postgres_custom_dump(local_file_path)
        elif fmt in ["sql_pg", "sql_mysql"]:
            struct_res = verify_sql_dump(local_file_path, fmt)
        else:
            struct_res = {
                "status": "warn",
                "duration_ms": 1,
                "summary": f"Unsupported or unknown archive format: {fmt}",
                "evidence": {}
            }
            has_warnings = True

        res_struct = VerificationResult(
            id=f"res_{job.id}_struct",
            job_id=job.id,
            stage="structural",
            check_name="format_integrity",
            status=struct_res["status"],
            actual_value=fmt,
            duration_ms=struct_res["duration_ms"],
            evidence_json=struct_res.get("evidence", {}),
            error_summary=struct_res["summary"] if struct_res["status"] in ["fail", "warn"] else None
        )
        db.add(res_struct)
        if struct_res["status"] == "fail":
            has_critical_failure = True
        db.commit()

        # STAGE 5 & RECOVERY TEST (IF JOB_TYPE INCLUDES RECOVERY)
        if job.job_type in ["full", "recovery_test"] and not has_critical_failure:
            job.current_stage = "recovery_test"
            job.progress = 85
            db.commit()
            
            rto_target = policy.rto_target_seconds if policy else 300
            rec_result = run_recovery_test_orchestrator(local_file_path, fmt, rto_target)
            
            rec_test = RecoveryTest(
                id=f"rec_{job.id}",
                verification_job_id=job.id,
                artifact_id=artifact.id,
                recovery_profile=f"{fmt}_profile",
                environment_type=rec_result["environment_type"],
                restore_duration_ms=rec_result["restore_duration_ms"],
                assertions_passed=rec_result["assertions_passed"],
                assertions_failed=rec_result["assertions_failed"],
                cleanup_status=rec_result.get("cleanup_status", "cleaned"),
                rto_target_seconds=rto_target,
                rto_met=rec_result["rto_met"],
                status=rec_result["status"],
                diagnostics=rec_result.get("diagnostics", {})
            )
            db.add(rec_test)
            if rec_result["status"] == "failed":
                has_critical_failure = True
            db.commit()

        # STAGE 6: POLICY EVALUATION & CONCLUSION
        job.current_stage = "complete"
        job.progress = 100
        job.completed_at = datetime.utcnow()
        job.duration_ms = int((time.time() - job_start) * 1000)
        
        if has_critical_failure:
            job.status = "failed"
            job.error_summary = "Verification failed one or more critical security or structural assertions."
            artifact.source.last_failed_at = datetime.utcnow()
        elif has_warnings:
            job.status = "verified_with_warnings"
            artifact.source.last_verified_at = datetime.utcnow()
        else:
            job.status = "verified"
            artifact.source.last_verified_at = datetime.utcnow()

        db.commit()
        
        # STAGE 7: AUDIT LOGGING
        record_audit_log(
            db=db,
            actor_id=None,
            actor_email="system",
            action="verification_completed",
            resource_type="verification_job",
            resource_id=job.id,
            metadata={"status": job.status, "duration_ms": job.duration_ms, "artifact_id": artifact.id}
        )
        
        return job

    except Exception as e:
        job.status = "failed"
        job.error_summary = f"Pipeline execution error: {str(e)}"
        job.completed_at = datetime.utcnow()
        job.duration_ms = int((time.time() - job_start) * 1000)
        db.commit()
        return job
