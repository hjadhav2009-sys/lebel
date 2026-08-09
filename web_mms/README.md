# MMS Web — Phase 3

The multi-user catalog, consignment, and printing platform lives in this folder. The legacy desktop application remains untouched and runnable from the repository root.

## Start on Windows

Install Docker Desktop and Node.js, then run `START_MMS_WEB.bat`. It starts PostgreSQL, FastAPI, and the React frontend.

Phase 3 adds production label compilation and a paired Windows local print agent. Install and pair it from `print_agent`, then launch it with `START_MMS_PRINT_AGENT.bat`.

Real transport is intentionally off by default. Phase 3.1 additionally requires local authentication, a strong secret, secure cookies, a ready printer, and exact physically tested approvals. Complete `docs/PRODUCTION_ENABLEMENT_CHECKLIST.md`; do not enable transport before TSC validation.

## Verification

- Backend: `python -m pytest` from `backend/`.
- Frontend: `npm test && npm run typecheck && npm run build` from `frontend/`.
- Agent: `pytest && ruff check mms_print_agent tests && pyright mms_print_agent` from `print_agent/`.
