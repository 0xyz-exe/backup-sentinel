import hashlib
import json
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models import AuditLog
from app.security import sanitize_metadata

def record_audit_log(
    db: Session,
    actor_id: Optional[str],
    actor_email: Optional[str],
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> AuditLog:
    # 1. Fetch previous log entry to maintain tamper-evident cryptographic hash chain
    last_log = db.query(AuditLog).order_by(AuditLog.created_at.desc()).first()
    previous_hash = last_log.event_hash if last_log else "0" * 64
    
    clean_meta = sanitize_metadata(metadata or {})
    now = datetime.utcnow()
    
    # 2. Compute SHA-256 hash of (previous_hash + action + resource + metadata + timestamp)
    hasher = hashlib.sha256()
    raw_payload = f"{previous_hash}|{action}|{resource_type}|{resource_id}|{json.dumps(clean_meta, sort_keys=True)}|{now.isoformat()}"
    hasher.update(raw_payload.encode("utf-8"))
    event_hash = hasher.hexdigest()
    
    import uuid
    log_entry = AuditLog(
        id=f"audit_{uuid.uuid4().hex[:12]}",
        actor_id=actor_id,
        actor_email=actor_email,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        metadata_json=clean_meta,
        previous_hash=previous_hash,
        event_hash=event_hash,
        created_at=now
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return log_entry

def verify_audit_chain_integrity(db: Session) -> Dict[str, Any]:
    """Verify that no audit logs have been tampered with or removed."""
    logs = db.query(AuditLog).order_by(AuditLog.created_at.asc()).all()
    if not logs:
        return {"status": "valid", "total_records": 0, "message": "No audit records to verify."}
        
    prev_hash = "0" * 64
    tampered_ids = []
    
    for log in logs:
        if log.previous_hash != prev_hash:
            tampered_ids.append(log.id)
            break
            
        hasher = hashlib.sha256()
        raw_payload = f"{log.previous_hash}|{log.action}|{log.resource_type}|{log.resource_id}|{json.dumps(log.metadata_json, sort_keys=True)}|{log.created_at.isoformat()}"
        hasher.update(raw_payload.encode("utf-8"))
        expected_hash = hasher.hexdigest()
        
        if expected_hash != log.event_hash:
            tampered_ids.append(log.id)
            break
            
        prev_hash = log.event_hash
        
    if tampered_ids:
        return {
            "status": "compromised",
            "total_records": len(logs),
            "tampered_record_id": tampered_ids[0],
            "message": "Audit chain integrity verification failed! Discrepancy detected."
        }
        
    return {
        "status": "valid",
        "total_records": len(logs),
        "message": "All audit log entries cryptographically verified. Hash chain intact."
    }
