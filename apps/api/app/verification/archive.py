import os
import zipfile
import tarfile
import time
from pathlib import Path
from typing import Dict, Any
from app.config import settings

def verify_zip_archive(file_path: str) -> Dict[str, Any]:
    start_time = time.time()
    evidence: Dict[str, Any] = {
        "format": "zip",
        "file_count": 0,
        "total_uncompressed_bytes": 0,
        "compression_ratio": 1.0,
        "traversal_attempts": [],
        "crc_errors": [],
        "warnings": []
    }
    
    compressed_size = os.path.getsize(file_path)
    if compressed_size == 0:
        return {
            "status": "fail",
            "duration_ms": int((time.time() - start_time) * 1000),
            "summary": "ZIP archive is zero bytes / empty file",
            "evidence": evidence
        }
        
    try:
        with zipfile.ZipFile(file_path, "r") as zf:
            # 1. Test CRC-32 on all members
            bad_file = zf.testzip()
            if bad_file:
                evidence["crc_errors"].append(bad_file)
                return {
                    "status": "fail",
                    "duration_ms": int((time.time() - start_time) * 1000),
                    "summary": f"Corrupted file found in ZIP archive (CRC-32 failure): {bad_file}",
                    "evidence": evidence
                }
                
            # 2. Inspect members for path traversal & zip bomb
            infolist = zf.infolist()
            evidence["file_count"] = len(infolist)
            total_uncompressed = sum(info.file_size for info in infolist)
            evidence["total_uncompressed_bytes"] = total_uncompressed
            
            if compressed_size > 0:
                ratio = total_uncompressed / compressed_size
                evidence["compression_ratio"] = round(ratio, 2)
                if ratio > settings.MAX_DECOMPRESSED_RATIO and total_uncompressed > 50 * 1024 * 1024:
                    return {
                        "status": "fail",
                        "duration_ms": int((time.time() - start_time) * 1000),
                        "summary": f"Suspicious compression ratio ({ratio:.1f}x) exceeds safety threshold (Decompression bomb risk).",
                        "evidence": evidence
                    }
                    
            for info in infolist:
                # Check for Zip Slip / Path Traversal
                name = info.filename
                if name.startswith("/") or name.startswith("\\") or ".." in name.split("/") or ".." in name.split("\\"):
                    evidence["traversal_attempts"].append(name)
                    
            if evidence["traversal_attempts"]:
                return {
                    "status": "fail",
                    "duration_ms": int((time.time() - start_time) * 1000),
                    "summary": f"Security violation: Archive contains dangerous path traversal entries: {evidence['traversal_attempts'][:3]}",
                    "evidence": evidence
                }
                
            return {
                "status": "pass",
                "duration_ms": int((time.time() - start_time) * 1000),
                "summary": f"ZIP archive structurally valid. Verified {len(infolist)} entries ({total_uncompressed} bytes uncompressed).",
                "evidence": evidence
            }
    except zipfile.BadZipFile as e:
        return {
            "status": "fail",
            "duration_ms": int((time.time() - start_time) * 1000),
            "summary": f"Malformed or corrupted ZIP file header: {str(e)}",
            "evidence": evidence
        }
    except Exception as e:
        return {
            "status": "fail",
            "duration_ms": int((time.time() - start_time) * 1000),
            "summary": f"Unexpected error reading ZIP archive: {str(e)}",
            "evidence": evidence
        }

def verify_tar_archive(file_path: str) -> Dict[str, Any]:
    start_time = time.time()
    evidence: Dict[str, Any] = {
        "format": "tar",
        "file_count": 0,
        "total_uncompressed_bytes": 0,
        "traversal_attempts": [],
        "warnings": []
    }
    
    file_size = os.path.getsize(file_path)
    if file_size == 0:
        return {
            "status": "fail",
            "duration_ms": int((time.time() - start_time) * 1000),
            "summary": "TAR archive is zero bytes / empty file",
            "evidence": evidence
        }
        
    try:
        # Open with automatic transparent compression mode (r:*)
        with tarfile.open(file_path, "r:*") as tf:
            members = tf.getmembers()
            evidence["file_count"] = len(members)
            total_uncompressed = sum(m.size for m in members)
            evidence["total_uncompressed_bytes"] = total_uncompressed
            
            for m in members:
                name = m.name
                if name.startswith("/") or name.startswith("\\") or ".." in name.split("/") or ".." in name.split("\\"):
                    evidence["traversal_attempts"].append(name)
                    
            if evidence["traversal_attempts"]:
                return {
                    "status": "fail",
                    "duration_ms": int((time.time() - start_time) * 1000),
                    "summary": f"Security violation: TAR archive contains path traversal entries: {evidence['traversal_attempts'][:3]}",
                    "evidence": evidence
                }
                
            return {
                "status": "pass",
                "duration_ms": int((time.time() - start_time) * 1000),
                "summary": f"TAR archive structurally valid. Verified {len(members)} entries ({total_uncompressed} bytes uncompressed).",
                "evidence": evidence
            }
    except tarfile.TarError as e:
        return {
            "status": "fail",
            "duration_ms": int((time.time() - start_time) * 1000),
            "summary": f"Corrupted or invalid TAR archive: {str(e)}",
            "evidence": evidence
        }
    except Exception as e:
        return {
            "status": "fail",
            "duration_ms": int((time.time() - start_time) * 1000),
            "summary": f"Unexpected error reading TAR archive: {str(e)}",
            "evidence": evidence
        }
