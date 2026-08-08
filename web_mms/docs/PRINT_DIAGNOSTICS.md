# Print diagnostics

The Print Job drawer exposes renderer identity, layout version, artifact SHA-256/size, overflow decisions, state events, assigned agent, spool job ID, and transport errors. The agent `--diagnostics` option creates a sanitized ZIP containing OS and printer discovery data; it excludes tokens and artifact content.

For `transport_failed`, confirm the failure happened before Windows accepted the document, fix the queue/driver, and create or reclaim only through the supported workflow. For `uncertain`, inspect the Windows spooler and physical labels first. Never auto-retry uncertain jobs. Compare downloaded bytes with the artifact SHA when investigating corruption.
