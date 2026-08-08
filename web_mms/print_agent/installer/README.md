# MMS Print Agent installer

Run `INSTALL_REQUIREMENTS.bat`, pair with `START_PRINT_AGENT.bat --pair 1234-5678`, and then launch `START_PRINT_AGENT.bat`.
Use `BUILD_AGENT.bat` to create `dist\MMSPrintAgent.exe`. Production startup should use Windows Task Scheduler under the paired user so the DPAPI-protected token remains accessible.

Real printing requires both server `MMS_PRINT_TRANSPORT_ENABLED=true` and agent `MMS_AGENT_TRANSPORT_ENABLED=true` with `MMS_AGENT_DRY_RUN=false`.
