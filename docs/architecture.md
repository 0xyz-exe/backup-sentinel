# Backup Sentinel — System Architecture

```mermaid
graph TD
    User["SRE / DBA / DevOps"] --> WebUI["Next.js Dashboard"]
    WebUI --> API["FastAPI Control Plane /api/v1"]
    API --> Auth["RBAC & JWT Token Service"]
    API --> DB[("Metadata DB (PostgreSQL / SQLite)")]
    API --> Audit["Tamper-Evident SHA-256 Audit Chain"]
    
    API --> StorageLayer["Storage Adapter Layer"]
    StorageLayer --> LocalFS["Local Filesystem Adapter (Boundary Checks)"]
    StorageLayer --> S3["S3-Compatible Object Storage Adapter"]

    API --> Engine["7-Stage Verification Engine"]
    Engine --> S1["Stage 1: Discovery & Path Containment"]
    Engine --> S2["Stage 2: Accessibility & Non-Zero Size"]
    Engine --> S3["Stage 3: Cryptographic SHA-256 Stream"]
    Engine --> S4["Stage 4: Structural Format Inspection"]
    Engine --> S5["Stage 5: Database Dialect Validation"]
    Engine --> S6["Stage 6: Policy & RTO/RPO Compliance Evaluation"]
    Engine --> S7["Stage 7: Evidence Collection & Immutable Audit"]

    Engine --> Sandbox["Recovery Sandbox Orchestrator"]
    Sandbox --> DisposableFS["Isolated Filesystem Sandbox"]
    Sandbox --> DisposableDB["Disposable Database Sandbox"]
```

## Architectural Principles
1. **Local-First & Cloud-Agnostic**: Operates with zero required cloud dependencies.
2. **Strict Boundary Isolation**: Untrusted backup contents never execute against host or production resources.
3. **Auditable Evidence**: Checksums, durations, and assertion details are permanently logged in cryptographic audit chains.
4. **Automated Cleanup**: Disposable recovery sandboxes are guaranteed to be destroyed in `finally` execution blocks.
