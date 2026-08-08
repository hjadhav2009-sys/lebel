# Reprint Workflow

Printed rows come only from successful `PrintJobLine` completions scoped to the same consignment line. A prepared or failed job does not mark a line Printed.

The default `Reprint Exact Snapshot` action creates a new print job and copies successful historical snapshots verbatim. It never edits the old job, changes its event history, or moves the original consignment line back to To Print. A future current-data reprint must require explicit confirmation because current data may differ.

Development simulation is disabled by default. When `MMS_ENABLE_PRINT_SIMULATION=true`, an Admin may produce successful completion events through a UI marked `SIMULATION`. This is test support, not printer transport.
