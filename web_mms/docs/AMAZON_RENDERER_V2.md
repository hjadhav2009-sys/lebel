# Amazon renderer v2

`amazon_dynamic_tspl_v2` is a new immutable identity; v1 remains installed for historical reprints. V2 reads only the print-line snapshot and renders the product rows, snapshot Net Quantity, shared MRP, full customer-care address/email/contact/origin, native and readable FNSKU, and bottom title. ASIN is not visible.

Coordinates are profile data. Fit validation covers required strings, barcode protected zone, address line count, and label bounds. Overflow blocks with `LABEL_TEXT_OVERFLOW`. Preview shares layout calculation; native font preview is guidance and physical TSC output is authoritative.

