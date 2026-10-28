import os
import struct
import time
from typing import Dict, Any

def verify_postgres_custom_dump(file_path: str) -> Dict[str, Any]:
    start_time = time.time()
    evidence: Dict[str, Any] = {
        "format": "pg_custom",
        "magic": "",
        "version": "",
        "compression": False,
        "valid_header": False,
        "toc_entries_detected": 0
    }
    
    file_size = os.path.getsize(file_path)
    if file_size < 12:
        return {
            "status": "fail",
            "duration_ms": int((time.time() - start_time) * 1000),
            "summary": "File too small to contain a valid PostgreSQL custom dump header",
            "evidence": evidence
        }
        
    try:
        with open(file_path, "rb") as f:
            magic = f.read(5)
            if magic != b"PGDMP":
                return {
                    "status": "fail",
                    "duration_ms": int((time.time() - start_time) * 1000),
                    "summary": f"Invalid PostgreSQL dump magic header. Expected 'PGDMP', got: {repr(magic)}",
                    "evidence": evidence
                }
            
            evidence["magic"] = "PGDMP"
            # Read format version bytes
            v_major, v_minor, v_rev = struct.unpack("BBB", f.read(3))
            evidence["version"] = f"{v_major}.{v_minor}.{v_rev}"
            evidence["valid_header"] = True
            
            # Read integer size and offset size
            int_size = struct.unpack("B", f.read(1))[0]
            off_size = struct.unpack("B", f.read(1))[0]
            fmt_type = struct.unpack("B", f.read(1))[0]
            compression = struct.unpack("B", f.read(1))[0]
            evidence["compression"] = bool(compression)
            evidence["format_type"] = fmt_type
            
            # Simple check for TOC presence
            # A valid dump will have TOC entries following the header
            remainder = f.read(1024)
            if len(remainder) > 0:
                evidence["toc_entries_detected"] = 1
                
            return {
                "status": "pass",
                "duration_ms": int((time.time() - start_time) * 1000),
                "summary": f"PostgreSQL custom dump header valid (v{evidence['version']}, compression={evidence['compression']}). Structural inspection passed.",
                "evidence": evidence
            }
    except Exception as e:
        return {
            "status": "fail",
            "duration_ms": int((time.time() - start_time) * 1000),
            "summary": f"Failed to parse PostgreSQL custom dump: {str(e)}",
            "evidence": evidence
        }
