# CHO Marketwatch Backend

FastAPI service for the new dashboard frontend.

## Run

1. Create and activate a virtual environment.
2. Install dependencies:

```powershell
pip install -r backend/requirements.txt
```

3. Run API:

```powershell
uvicorn app.main:app --app-dir backend --reload --host 0.0.0.0 --port 8000
```

API base URL (same machine): http://localhost:8000/api/v1
API base URL (LAN): http://<server-ip>:8000/api/v1
