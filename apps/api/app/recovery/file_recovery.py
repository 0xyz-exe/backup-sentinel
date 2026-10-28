import os
import shutil
import tempfile
import time
import zipfile
import tarfile
from pathlib import Path
from typing import Dict, Any

def execute_generic_archive_recovery_test(file_path: str, format_type: str, rto_target_seconds: int = 300) -> Dict[str, Any]:
    start_time = time.time()
    sandbox_dir = tempfile.mkdtemp(prefix="sentinel_sandbox_")
    cleanup_status = "pending"
    assertions_passed = 0
    assertions_failed = 0
    extracted_files = []
    
    try:
        sandbox_path = Path(sandbox_dir).resolve()
        
        if format_type == "zip":
            with zipfile.ZipFile(file_path, "r") as zf:
                for member in zf.infolist():
                    target = (sandbox_path / member.filename).resolve()
                    # Security check: verify extraction target stays inside sandbox
                    if not str(target).startswith(str(sandbox_path)):
                        assertions_failed += 1
                        raise PermissionError(f"Path traversal detected during extraction: {member.filename}")
                    zf.extract(member, sandbox_path)
                    if not member.is_dir():
                        extracted_files.append(target)
                        
        elif format_type == "tar":
            with tarfile.open(file_path, "r:*") as tf:
                for member in tf.getmembers():
                    target = (sandbox_path / member.name).resolve()
                    if not str(target).startswith(str(sandbox_path)):
                        assertions_failed += 1
                        raise PermissionError(f"Path traversal detected during extraction: {member.name}")
                    tf.extract(member, sandbox_path)
                    if member.isfile():
                        extracted_files.append(target)
        else:
            raise ValueError(f"Unsupported archive format for generic recovery: {format_type}")
            
        # Assertion 1: At least one file restored
        if len(extracted_files) > 0:
            assertions_passed += 1
        else:
            assertions_failed += 1
            
        # Assertion 2: All extracted files exist and are readable on disk
        readable_count = 0
        for f in extracted_files:
            if f.exists() and f.is_file():
                readable_count += 1
        if readable_count == len(extracted_files):
            assertions_passed += 1
        else:
            assertions_failed += 1

        restore_duration_ms = int((time.time() - start_time) * 1000)
        rto_met = (restore_duration_ms / 1000.0) <= rto_target_seconds
        
        status = "passed" if assertions_failed == 0 else "failed"
        
        return {
            "status": status,
            "environment_type": "disposable_filesystem_sandbox",
            "restore_duration_ms": restore_duration_ms,
            "assertions_passed": assertions_passed,
            "assertions_failed": assertions_failed,
            "rto_target_seconds": rto_target_seconds,
            "rto_met": rto_met,
            "diagnostics": {
                "extracted_file_count": len(extracted_files),
                "sandbox_location": "sanitized_temp_sandbox",
                "files_verified": [p.name for p in extracted_files[:10]]
            }
        }
    except Exception as e:
        restore_duration_ms = int((time.time() - start_time) * 1000)
        return {
            "status": "failed",
            "environment_type": "disposable_filesystem_sandbox",
            "restore_duration_ms": restore_duration_ms,
            "assertions_passed": assertions_passed,
            "assertions_failed": assertions_failed + 1,
            "rto_target_seconds": rto_target_seconds,
            "rto_met": False,
            "diagnostics": {
                "error": str(e),
                "extracted_file_count": len(extracted_files)
            }
        }
    finally:
        # Mandatory cleanup of disposable recovery environment
        try:
            if os.path.exists(sandbox_dir):
                shutil.rmtree(sandbox_dir, ignore_errors=True)
            cleanup_status = "cleaned"
        except Exception:
            cleanup_status = "failed"
