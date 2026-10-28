# Threat Model & Security Boundaries

## 1. Overview
Backup Sentinel operates in a high-security context because it routinely ingests, parses, and executes recovery procedures against backup artifacts. If an attacker tampers with or crafts a malicious backup file, the system must remain resilient.

## 2. Threat Vectors & Mitigations

### 2.1 Malicious Archive Contents (Zip-Slip / Directory Traversal)
- **Threat**: An archive containing file paths such as `../../etc/shadow` or absolute paths aiming to overwrite host files upon extraction.
- **Mitigation**: Every archive inspection and extraction strictly evaluates the canonical target path against the sandbox boundary before extraction. If `canonical_path.startswith(sandbox_root)` is false, extraction halts immediately with a security violation.

### 2.2 Decompression Bombs (Zip-Bomb / Gz-Bomb)
- **Threat**: Extremely compressed payloads (e.g. 42.zip) designed to exhaust server disk space and RAM.
- **Mitigation**: Sentinel tracks uncompressed byte sizes and evaluates decompression ratios. Any payload exceeding a 100:1 ratio or 10 GB limit is aborted before processing.

### 2.3 Untrusted Code / Database Dump Injection
- **Threat**: An SQL dump containing dangerous admin commands or shell escape sequences (e.g., PostgreSQL `COPY ... FROM PROGRAM`).
- **Mitigation**:
  1. Plain SQL dumps are analyzed through lexical sanitizers that filter out dialect-specific executable commands.
  2. Recovery tests execute exclusively in disposable, non-root isolated container or isolated memory sandboxes with no access to production databases.

### 2.4 Arbitrary Filesystem Traversal
- **Threat**: A user submitting an arbitrary root path (e.g. `/` or `C:\Windows`) for local backup discovery.
- **Mitigation**: The Local Filesystem Adapter strictly validates all configured paths against allowlisted storage boundaries defined in `ALLOWED_STORAGE_ROOTS`. Symlink escapes are caught and rejected.

### 2.5 Audit Log Tampering
- **Threat**: A malicious insider modifying database records to erase evidence of a compromised verification.
- **Mitigation**: Audit logs employ SHA-256 cryptographic hash-chaining:
  `event_hash = SHA256(previous_hash | action | resource_type | resource_id | metadata | timestamp)`
  Any altered, reordered, or deleted record invalidates the entire verification chain.
