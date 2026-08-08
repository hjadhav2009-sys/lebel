# Amazon Consignment Matching

Amazon consignment import detects headers across CSV/XLSX/XLSM sheets. Recognized aliases include Merchant SKU, Seller SKU, SKU, Title, ASIN, FNSKU, Shipped, and Quantity Shipped.

Matching is scoped to the selected Amazon account:

1. Exact normalized seller/Merchant SKU when the row provides a SKU.
2. Unique FNSKU only when SKU is absent.
3. Unique ASIN only when both SKU and FNSKU are absent.

A present but unknown SKU does not fall through to ASIN. This prevents two seller SKUs sharing an ASIN from merging. `Shipped` becomes both source quantity and Print Quantity. MRP comes from the matched catalog; missing MRP creates `MISSING_MRP`. Numeric line MRP overrides do not mutate the catalog.
