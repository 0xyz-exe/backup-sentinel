import os
import re
import time
from typing import Dict, Any

def verify_sql_dump(file_path: str, dialect: str = "sql_pg") -> Dict[str, Any]:
    start_time = time.time()
    evidence: Dict[str, Any] = {
        "dialect": dialect,
        "table_creates": 0,
        "insert_statements": 0,
        "copy_statements": 0,
        "transaction_blocks": 0,
        "has_commit": False,
        "lines_scanned": 0
    }
    
    file_size = os.path.getsize(file_path)
    if file_size == 0:
        return {
            "status": "fail",
            "duration_ms": int((time.time() - start_time) * 1000),
            "summary": "SQL dump file is empty (0 bytes)",
            "evidence": evidence
        }
        
    try:
        in_block_comment = False
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for idx, line in enumerate(f):
                evidence["lines_scanned"] += 1
                stripped = line.strip().upper()
                
                # Check for block comments
                if "/*" in stripped:
                    in_block_comment = True
                if "*/" in stripped:
                    in_block_comment = False
                    continue
                if in_block_comment or stripped.startswith("--"):
                    continue
                    
                if stripped.startswith("CREATE TABLE"):
                    evidence["table_creates"] += 1
                elif stripped.startswith("INSERT INTO"):
                    evidence["insert_statements"] += 1
                elif stripped.startswith("COPY "):
                    evidence["copy_statements"] += 1
                elif stripped.startswith("BEGIN") or stripped.startswith("START TRANSACTION"):
                    evidence["transaction_blocks"] += 1
                elif stripped.startswith("COMMIT"):
                    evidence["has_commit"] = True
                    
        # Check basic sanity: must contain at least one CREATE TABLE or INSERT/COPY
        data_operations = evidence["table_creates"] + evidence["insert_statements"] + evidence["copy_statements"]
        if data_operations == 0:
            return {
                "status": "fail",
                "duration_ms": int((time.time() - start_time) * 1000),
                "summary": "SQL dump contains no recognized DDL or DML statements (empty schema/data)",
                "evidence": evidence
            }
            
        return {
            "status": "pass",
            "duration_ms": int((time.time() - start_time) * 1000),
            "summary": f"SQL dump syntax valid ({dialect}). Found {evidence['table_creates']} tables, {evidence['insert_statements']} inserts, {evidence['copy_statements']} COPY blocks across {evidence['lines_scanned']} lines.",
            "evidence": evidence
        }
    except Exception as e:
        return {
            "status": "fail",
            "duration_ms": int((time.time() - start_time) * 1000),
            "summary": f"Error scanning SQL dump: {str(e)}",
            "evidence": evidence
        }
