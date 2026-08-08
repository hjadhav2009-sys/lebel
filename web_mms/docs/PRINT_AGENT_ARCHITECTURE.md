# Print agent architecture

The central FastAPI/PostgreSQL service owns jobs, immutable artifacts, leases, approvals, and audit events. Printing PCs run the Windows-only agent beside the TSC driver. Worker PCs use only the browser; PostgreSQL is never exposed to them.

The agent authenticates with a revocable bearer token, discovers Windows queues, polls for a job assigned through an enabled printer profile, downloads exact bytes, verifies SHA-256 and length, and submits one RAW document through `win32print`. Handles and documents are closed in `finally` blocks. No shell command or browser direct-print route exists.

Production uses HTTPS. Both server and agent transport switches default off. Future BarTender, TSC SDK, and Windows GDI adapters implement the existing renderer/transport boundaries without changing Catalog, Consignment, Print Queue, or agent job contracts.
