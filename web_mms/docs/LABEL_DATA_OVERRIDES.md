# Label Data Overrides

`ConsignmentLabelDataService` resolves each field in this order: explicit consignment-line override, catalog value, marketplace-derived value, then Missing. Required Missing fields create blocking structured issues; the service never fabricates data.

Resolved fields carry a source badge: `Consignment Override`, `Catalog`, `Derived`, or `Missing`. Print snapshots preserve both values and their sources.

Line edits are deliberately independent. MRP, Net Quantity value/unit, Print Quantity, title, brand, format, generic name, Model Name, and Model Number are separately validated and audited. Model Name and Model Number remain distinct. `Update Catalog` is a separate permanent operation.
