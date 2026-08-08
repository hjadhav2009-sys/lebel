# MMS Web — Phase 1

The new MMS catalog platform lives entirely in this folder. The legacy desktop application remains untouched and runnable from the repository root.

## Start on Windows

Install Docker Desktop and Node.js, then double-click `START_MMS_WEB.bat`. It starts PostgreSQL and FastAPI, installs frontend dependencies on first use, starts the React development server, waits for the backend health check, and opens the browser.

Manual setup and production considerations are documented in `docs/ARCHITECTURE.md`.

## Verification

Backend: `python -m pytest` from `backend/`.

Frontend: `npm run build` from `frontend/`.

No label rendering or raw printer transport is implemented in this phase.
