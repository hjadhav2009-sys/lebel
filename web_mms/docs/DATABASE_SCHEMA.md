# Database schema

| Area | Tables | Purpose |
|---|---|---|
| Identity | `users`, `roles`, `user_roles` | Multi-user access and role foundations |
| Accounts | `marketplace_accounts` | Seller account boundary for every product |
| Catalog | `catalog_products`, `catalog_identifiers`, `product_images` | Current normalized catalog, flexible IDs, image metadata |
| Imports | `catalog_imports`, `catalog_import_rows`, `import_errors` | Immutable import runs, raw rows, decisions, structured issues |
| Workflow | `consignments`, `consignment_lines` | Future shared Amazon/Flipkart workspace |
| Printing | `print_jobs`, `print_job_lines`, `label_format_profiles` | Future job snapshots; no transport in Phase 1 |
| Configuration | `address_profiles`, `mapping_profiles` | Account-aware reusable settings |
| Audit | `audit_events` | Actor, timestamp, field changes, and context |
| Catalog batches | `catalog_batches` | Multi-file account-scoped weekly catalog runs |
| Print foundation | `print_agents`, `printers`, `printer_profiles` | Outbound Windows agents and configuration; no transport yet |

UUIDs are used for business entities; small static roles use integer IDs. Money uses `NUMERIC(12,2)`. Raw and normalized rows, snapshots, profile configuration, and marketplace extras use PostgreSQL JSON. Foreign keys, account/business-key uniqueness, import-row uniqueness, and query indexes are created in Alembic revision `20260808_0001`.

The initial revision is an explicit, reviewable Alembic migration using table/index/constraint operations. It no longer delegates schema creation or destruction to ORM metadata.
