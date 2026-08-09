# Canonical label-field resolution

Field names are trimmed, case-folded, and punctuation/space/hyphen runs become underscores. Validation, resolved-label data, snapshots, and renderer lookup share this contract.

Priority is consignment override, direct operational snapshot, catalog core, catalog `extra_attributes`, approved derived value, then Missing. Effective values carry `Catalog`, `Consignment Override`, `Derived`, or `Missing`.

Shipping/package dimensions are not aliases for product `dimensions`. A mapping must explicitly populate canonical dimensions. Missing Flipkart dimensions blocks with `MISSING_DIMENSIONS`. Model Name is never inferred from Model Number.

