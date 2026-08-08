# Product Drawer

The Product Drawer is the detailed product workspace and does not navigate away from Inventory.

- **Overview** shows seller account, identifiers, catalog fields, provenance, and timestamps. Identifier copy actions are explicit.
- **Images** is the only UI that renders product images. It supports multiple images, metadata, a lightbox, original URLs, and a non-blocking enrichment request. Flipkart enrichment is not run during catalog imports.
- **Label Data** separates future consignment-only values from permanent catalog updates. Permanent updates must be confirmed and audited before production rollout.
- **Print History** reads durable print job lines and has a real empty state.
- **Change History** reads product audit events; it contains no fabricated timeline entries.

Image sources are merged by importer source. Manual and enrichment images are preserved. Replaced imported images are marked stale rather than destroyed.
