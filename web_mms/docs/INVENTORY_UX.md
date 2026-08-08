# Inventory UX

Inventory is a server-driven operations table designed for 200,000 or more products. Search, filters, sorting, pagination, and totals are API queries; the browser never downloads the catalog for local filtering. Search covers SKU, ASIN, FNSKU, FSN, Listing ID, title, and brand through indexed product and identifier queries.

The table intentionally contains no image elements. Image status is text only, preventing marketplace image requests during scrolling. Rows are keyboard-focusable, the header is sticky, visible rows can be selected, columns can be hidden, and density can be changed. Opening a row retains the Inventory context and presents the Product Drawer.

Loading, empty, request-error, and stale-request cancellation are explicit states. Search is debounced. API totals control pagination and statistics; no demonstration counts are used.
