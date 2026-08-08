# Architecture

MMS Web is a multi-user catalog system with a React/TypeScript browser client, a FastAPI service layer, SQLAlchemy repositories, Alembic migrations, and PostgreSQL. It is isolated from the desktop V47 application.

The frontend calls versioned `/api/v1` endpoints. Route handlers validate transport data, repositories own query construction, and services own imports and audit behavior. PostgreSQL is authoritative; browser storage is used only for UI preferences such as theme.

Product identity is scoped to a marketplace account. An account represents one seller presence, such as Amazon / Mumbai Seller. A product row uses a stable business key and normalized SHA-256 fingerprint. Marketplace identifiers and images are child records, avoiding a marketplace-specific mega-table. Category-specific values live in structured extra attributes and remain present in raw import JSON.

Authentication foundations consist of users, roles, user-role assignment, actor columns, and audit events. Roles are Admin, QC, Packing, and Print Operator. Production identity-provider choice and credential rollout should be completed before exposing the service outside the trusted network.

Phase 1.5 splits versioned APIs into Inventory, Imports, Accounts, Errors, Users, Consignments, Print Queue, and Images routers. The frontend mirrors these domains with feature folders and shared tables, states, drawers, badges, and identifier controls. Development identity is explicitly marked and must be replaced by the production identity provider before external deployment.

Catalog queries stay in PostgreSQL. Product and identifier indexes support account-scoped search; imports and errors have provenance/status indexes; pagination never loads all rows into Python. For production sizing, use `EXPLAIN (ANALYZE, BUFFERS)` against representative 200k-product and million-import-row data before rollout and tune trigram/full-text indexes if substring search becomes the dominant cost.

PostgreSQL is the only required durable service in Phase 1. Image binaries are not copied into the database: canonical URLs and check status are stored. Future object storage can be added for cached thumbnails without changing product identity.

## Local development

`docker compose up -d --build` starts PostgreSQL and the API. The frontend is started with `npm install` and `npm run dev`. Apply migrations with `alembic upgrade head` from the backend environment.

## Operational boundaries

The API never sends raw data to a local printer. Future print jobs are durable server records retrieved by an authenticated localhost-only Windows agent. The desktop rendering code remains frozen until parity testing passes.
