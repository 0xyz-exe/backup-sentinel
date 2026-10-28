# Contributing to Backup Sentinel

Thank you for your interest in contributing to Backup Sentinel!

## Local Development Setup

### Backend (FastAPI + Python 3.12)
```bash
cd apps/api
uv venv --python 3.12 .venv
source .venv/bin/activate # or .venv\Scripts\activate on Windows
pip install -r requirements.txt email-validator
python -m app.cli seed --dir "../../fixtures/synthetic-backups"
PYTHONPATH=. pytest -v
uvicorn app.main:app --reload --port 8000
```

### Frontend (Next.js 14)
```bash
cd apps/web
pnpm install
pnpm run dev # http://localhost:3000
```

## Running Tests
- **Backend tests**: `PYTHONPATH=. pytest -v` inside `apps/api`
- **Frontend build test**: `pnpm run build` inside `apps/web`
