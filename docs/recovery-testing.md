# Automated Recovery Testing & Sandbox Orchestration

## Core Thesis
> *"A backup is not proven reliable until it has been successfully verified and its recovery process has been tested."*

## Recovery Workflow
1. **Target Artifact Selection**: Selected from discovered backup sources.
2. **Disposable Sandbox Provisioning**: A unique isolated sandbox (`sentinel_sandbox_<uuid>`) is instantiated inside a dedicated temp workspace.
3. **Extraction & Traversal Detection**: Each member file is extracted while validating its path resolution against the sandbox root.
4. **Integrity Assertions**:
   - `assertion_1`: Extracted file count matches TOC entries.
   - `assertion_2`: Restored files are accessible, non-empty, and structurally sound.
   - `assertion_3`: Table schemas and rows execute cleanly.
5. **RTO Measurement**: Actual recovery duration in milliseconds is measured and compared against the policy RTO target.
6. **Mandatory Destruction**: The sandbox is pruned and destroyed in a guaranteed `finally` block.
