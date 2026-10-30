
#!/usr/bin/env bash
# One-command local run: builds the frontend if needed, then serves everything from FastAPI on :8000.
set -e
cd "$(dirname "$0")"
[ -d backend/.venv ] || python3 -m venv backend/.venv
. backend/.venv/bin/activate && pip install -q -r backend/requirements.txt
[ -d frontend/dist ] || (cd frontend && npm install --silent && npm run build)
[ -f backend/.env ] && set -a && . backend/.env && set +a
cd backend && exec uvicorn app.main:app --host 0.0.0.0 --port 8000
