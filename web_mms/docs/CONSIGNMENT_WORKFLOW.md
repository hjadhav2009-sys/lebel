# Consignment Workflow

A catalog is the durable, account-scoped product record. A consignment is a new operational session created from a marketplace quantity source. Importing the same file into a new consignment intentionally creates fresh `to_print`, unselected lines; product identity never carries Printed state across consignments.

The worker creates a draft, selects marketplace and account, previews the best detected worksheet, and imports it. Matching and validation produce `to_print` or `blocked` lines. No imported row is automatically selected. Header selection affects only line IDs returned by the current server-side filter.

Temporary title, brand, MRP, net quantity, print quantity, format, generic-name, label-field, and address changes live on `ConsignmentLine`. A permanent catalog correction is a separate audited action. Optimistic versions reject stale edits with `CONSIMENT_LINE_CHANGED`.

`Finish & Archive` closes a workspace without deleting its lines or print history. `Start New` creates an independent session. There is no destructive global clear operation.

## Quantity invariant

Net Quantity describes the package contents printed on one label. Print Quantity is the number of label copies requested by the consignment source. Amazon `Shipped` and Flipkart quantity aliases set Print Quantity only; they never silently change Net Quantity.
