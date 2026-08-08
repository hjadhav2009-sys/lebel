# Print Job Snapshots

Preparing a print job considers only explicitly selected `to_print` lines with positive Print Quantity and no unresolved blocking issues. Preparation creates a job in `ready` plus immutable job-line snapshots; it does not mark source lines Printed.

Each snapshot contains marketplace, account, consignment, product and line IDs, SKU/ASIN/FNSKU/FSN/listing ID, title, brand, numeric MRP, Net Quantity, Print Quantity, format, generic name, full address profile, effective label fields, override sources, and `phase2-snapshot-v1` as the renderer placeholder.

Snapshots are copied values. Later catalog or consignment edits cannot alter historical payloads. Phase 2 stores no raw PRN/TSPL and performs no printer transport.

The explicit job states are draft, ready, waiting_for_agent, sending, printing, completed, partially_completed, failed, and cancelled. Normal Phase 2 operation stops at ready/waiting_for_agent.
