# Print Agent plan

Printing remains out of scope for Phase 1.5. The schema now has `print_agents`, `printers`, and `printer_profiles`, while Print Queue and Printers expose read-only foundations.

The future agent runs silently on Windows and makes an outbound authenticated connection to FastAPI. It reports machine, version, printers, driver names, DPI, and heartbeat state. The server assigns immutable print jobs; the agent sends approved bytes through the Windows spooler and reports results. No browser-direct printer API or inbound LAN listener is required.

Flow: Browser → FastAPI → PrintJob → outbound-connected MMS Print Agent → Windows spooler → TSC printer.
