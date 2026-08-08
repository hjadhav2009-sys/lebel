# Amazon dynamic TSPL renderer

`amazon_dynamic_tspl_v1` builds TSPL from Amazon snapshot data. It prints product identity, Net Quantity, a single shared MRP representation, generic name, marketed-by/address details, and a native Code 128 FNSKU barcode. Text is escaped and encoded strictly; invalid barcodes and control characters block rendering.

The layout is data-driven, DPI-aware, and deterministic. Copies expand before 2-up pairing, so an odd final count leaves the right slot blank and never duplicates a label. Profile geometry and offsets must be validated on the target TSC TE244 before approval.
