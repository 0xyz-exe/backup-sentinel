# Changelog

All notable changes to Backup Sentinel are documented in this file.

## [0.1.0] - 2026-10-28
### Added
- Complete 7-stage automated backup verification pipeline (Discovery, Accessibility, SHA-256 Stream, Structural, Database Dialect, Policy Evaluation, Immutable Evidence).
- Format-specific parsers for ZIP, TAR (gzip/bz2/xz), PostgreSQL custom format dumps (`PGDMP`), and plain SQL logical dumps.
- Isolated disposable recovery testing sandbox with automatic resource pruning and cleanup.
- Tamper-evident cryptographic audit log with SHA-256 hash chaining.
- FastAPI REST control plane under `/api/v1` with RBAC authorization and JWT security.
- Modern Next.js 14 operations dashboard with real-time health, source management, verification actions, and recovery monitoring.
- Docker Compose deployment configuration with PostgreSQL and health checks.
- Comprehensive automated test suite and GitHub Actions CI workflow.
