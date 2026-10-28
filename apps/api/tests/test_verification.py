import os
import pytest
from app.verification.checksum import calculate_sha256_stream
from app.verification.archive import verify_zip_archive, verify_tar_archive
from app.verification.postgres import verify_postgres_custom_dump
from app.verification.sql import verify_sql_dump
from app.recovery.file_recovery import execute_generic_archive_recovery_test
from app.recovery.orchestrator import execute_sql_recovery_test

FIXTURES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../fixtures/synthetic-backups"))

def test_checksum_calculation_and_mismatch():
    valid_zip = os.path.join(FIXTURES_DIR, "valid_app_backup.zip")
    assert os.path.exists(valid_zip)
    
    # 1. Calculation without reference
    with open(valid_zip, "rb") as f:
        res = calculate_sha256_stream(f)
    assert res["status"] == "pass"
    assert len(res["computed_checksum"]) == 64
    computed_hash = res["computed_checksum"]
    
    # 2. Calculation matching reference
    with open(valid_zip, "rb") as f:
        res_match = calculate_sha256_stream(f, expected_checksum=computed_hash)
    assert res_match["status"] == "pass"
    assert res_match["matches"] is True
    
    # 3. Calculation with mismatched reference
    with open(valid_zip, "rb") as f:
        res_mismatch = calculate_sha256_stream(f, expected_checksum="0" * 64)
    assert res_mismatch["status"] == "fail"
    assert res_mismatch["matches"] is False
    assert "CRITICAL: Checksum mismatch" in res_mismatch["summary"]

def test_zip_validation_and_security_traversal():
    valid_zip = os.path.join(FIXTURES_DIR, "valid_app_backup.zip")
    bad_zip = os.path.join(FIXTURES_DIR, "corrupted_archive.zip")
    traversal_zip = os.path.join(FIXTURES_DIR, "traversal_attack.zip")
    
    # Valid ZIP
    v_res = verify_zip_archive(valid_zip)
    assert v_res["status"] == "pass"
    assert v_res["evidence"]["file_count"] >= 3
    
    # Corrupted ZIP
    b_res = verify_zip_archive(bad_zip)
    assert b_res["status"] == "fail"
    
    # Traversal attack ZIP
    t_res = verify_zip_archive(traversal_zip)
    assert t_res["status"] == "fail"
    assert "Security violation" in t_res["summary"]

def test_tar_validation():
    valid_tar = os.path.join(FIXTURES_DIR, "valid_sys_backup.tar.gz")
    res = verify_tar_archive(valid_tar)
    assert res["status"] == "pass"
    assert res["evidence"]["file_count"] >= 2

def test_postgres_dump_validation():
    valid_pg = os.path.join(FIXTURES_DIR, "valid_postgres.dump")
    res = verify_postgres_custom_dump(valid_pg)
    assert res["status"] == "pass"
    assert res["evidence"]["magic"] == "PGDMP"
    assert res["evidence"]["valid_header"] is True

def test_sql_dump_validation():
    valid_sql = os.path.join(FIXTURES_DIR, "valid_database.sql")
    malformed_sql = os.path.join(FIXTURES_DIR, "malformed_database.sql")
    
    res_valid = verify_sql_dump(valid_sql)
    assert res_valid["status"] == "pass"
    assert res_valid["evidence"]["table_creates"] >= 1
    
    res_bad = verify_sql_dump(malformed_sql)
    assert res_bad["status"] == "fail"

def test_isolated_generic_recovery_and_cleanup():
    valid_zip = os.path.join(FIXTURES_DIR, "valid_app_backup.zip")
    rec = execute_generic_archive_recovery_test(valid_zip, "zip", rto_target_seconds=60)
    assert rec["status"] == "passed"
    assert rec["assertions_passed"] >= 2
    assert rec["assertions_failed"] == 0
    assert rec["rto_met"] is True
    assert rec["restore_duration_ms"] >= 0

def test_isolated_sql_recovery():
    valid_sql = os.path.join(FIXTURES_DIR, "valid_database.sql")
    rec = execute_sql_recovery_test(valid_sql, "sql_pg", rto_target_seconds=60)
    assert rec["status"] == "passed"
    assert rec["cleanup_status"] == "cleaned"
    assert rec["rto_met"] is True
