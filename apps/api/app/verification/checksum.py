import hashlib
import time
from typing import BinaryIO, Dict, Any, Optional

def calculate_sha256_stream(stream: BinaryIO, expected_checksum: Optional[str] = None) -> Dict[str, Any]:
    start_time = time.time()
    sha256 = hashlib.sha256()
    bytes_read = 0
    
    # Read in 64KB blocks to prevent high memory usage
    chunk_size = 65536
    while True:
        chunk = stream.read(chunk_size)
        if not chunk:
            break
        sha256.update(chunk)
        bytes_read += len(chunk)
        
    computed = sha256.hexdigest().lower()
    duration_ms = int((time.time() - start_time) * 1000)
    
    result = {
        "algorithm": "SHA-256",
        "computed_checksum": computed,
        "expected_checksum": expected_checksum.lower() if expected_checksum else None,
        "bytes_verified": bytes_read,
        "duration_ms": duration_ms,
        "matches": None,
        "status": "pass",
        "summary": ""
    }
    
    if expected_checksum:
        expected = expected_checksum.strip().lower()
        if computed == expected:
            result["matches"] = True
            result["status"] = "pass"
            result["summary"] = "Cryptographic checksum matches verified reference value exactly."
        else:
            result["matches"] = False
            result["status"] = "fail"
            result["summary"] = f"CRITICAL: Checksum mismatch. Computed {computed} does not match expected {expected}."
    else:
        result["matches"] = None
        result["status"] = "pass"
        result["summary"] = "Checksum calculated successfully. No external reference checksum was provided for comparison."
        
    return result
