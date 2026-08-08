# MMS Windows Print Agent

The agent discovers Windows print queues and submits server-compiled TSPL as one `RAW` spool document. It does not render labels or read catalog data.

1. Run `INSTALL_REQUIREMENTS.bat`.
2. Generate a pairing code in the Printers page.
3. Run `START_PRINT_AGENT.bat --pair 1234-5678`.
4. Start normally with `START_PRINT_AGENT.bat`.

The default is dry-run with real transport disabled. Physical output requires `MMS_AGENT_TRANSPORT_ENABLED=true`, `MMS_AGENT_DRY_RUN=false`, and server `MMS_PRINT_TRANSPORT_ENABLED=true`. A job remains `spooled` after Windows accepts it; an operator confirms physical output in the web UI.

Use `START_PRINT_AGENT.bat --diagnostics` for a sanitized diagnostics ZIP. Build the standalone executable with `BUILD_AGENT.bat`.
