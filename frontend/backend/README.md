# ClearClaim Option A API

## Backend (FastAPI)

Run from `backend/`:

```bash
pip install -r requirements.txt
$env:CLEARCLAIM_ROOT=\"..\\ClearClaim\"
$env:CLEARCLAIM_DB_PATH=\".\\data\\clearclaim.db\"
uvicorn main:app --reload --port 8000
```

## Environment variable loading

On startup, the backend auto-loads env vars from:
- `..\\ClearClaim\\.env` (if present)
- `backend\\.env` (if present)

This allows `ANTHROPIC_API_KEY` to be shared from the ClearClaim repo without re-exporting it every session.

## Frontend connection

In repo root, create `.env` from `.env.example`.

- Live backend mode:
  - `VITE_API_MODE=live`
  - `VITE_API_BASE_URL=http://127.0.0.1:8000`
- Mock mode:
  - `VITE_API_MODE=mock`

## Endpoints
- POST `/api/v1/patient/estimate`
- POST `/api/v1/hospital/denial`
- POST `/api/v1/hospital/{run_id}/reevaluate`
- GET `/api/v1/runs/{run_id}`
- GET `/api/v1/sessions/{session_id}`
