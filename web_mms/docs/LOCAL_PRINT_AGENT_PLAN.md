# Local Print Agent plan

Phase 1 contains a boundary only; it does not migrate printing.

The future Windows agent will listen on loopback only, require a short-lived server-issued token, allow only configured printers, and reject arbitrary file paths or commands. It will poll or receive assigned print-job IDs, download an immutable label snapshot, render through a versioned adapter, submit bytes through the Windows spooler, and acknowledge success or a structured failure.

Renderer adapters may wrap the current validated PRN engine, a dynamic raster/native barcode renderer, BarTender, or the TSC SDK. Inventory and consignments will not depend on a specific adapter.

Every print result will record printer, workstation identity, renderer version, exact label data, label count, operator, timestamps, and spooler outcome. Retry creates a new attempt without erasing the original. The agent must never expose a LAN listener, accept unauthenticated browser content, or let a job select an unapproved executable.
