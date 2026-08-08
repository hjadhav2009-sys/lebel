# Migration from desktop

V47 remains the operational fallback. Root `main.py`, `app/`, `marketplace_v12/`, and `tools/` are not imported by or modified for MMS Web.

1. Phase 1 establishes accounts, catalog schema, incremental imports, Inventory, structured errors, and audit foundations.
2. Validate real Amazon and Flipkart files in a non-production account. Reconcile New / Updated / Unchanged / Error totals with the desktop process.
3. Add consignments while desktop printing remains authoritative.
4. Implement the local agent and run side-by-side label parity tests by format, printer DPI, barcode scan, overflow case, and quantity.
5. Move operators only after catalog counts, blocking validation, label output, reprint audit, and recovery procedures pass acceptance.

No automatic migration deletes source rows. Import corrections create new import runs; manual changes create audit events. Rollback during the transition means returning the operator to V47, not rewriting or downgrading its files.
