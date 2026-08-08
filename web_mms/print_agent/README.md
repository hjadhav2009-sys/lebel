# MMS Print Agent (Phase 1 scaffold)

This folder intentionally contains no printer implementation yet. The future Windows-only agent will bind to localhost, authenticate job requests, enumerate approved printers, send raw PRN/TSPL through the Windows spooler, and report an immutable result to the web server.

Printing code in the legacy desktop application remains the source of truth until label parity is verified. See `docs/LOCAL_PRINT_AGENT_PLAN.md`.
