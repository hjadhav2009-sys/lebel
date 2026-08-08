# Error handling

API failures use `{ "code", "message", "details" }`. The UI provides loading, empty, and error states instead of silent fallbacks.

Each import row runs in a database savepoint. Validation, integrity, data, and unexpected row exceptions create a `catalog_import_rows` error decision and related `import_errors` record without discarding successful rows. Imports with any row failures finish as `COMPLETED_WITH_ERRORS`; catastrophic execution failures finish as `FAILED` and are not presented as successful.

`FORMULA_RESULT_MISSING` means a required formula cell had no cached Excel result. The raw formula is never used as catalog data. The operator must recalculate and save the workbook before importing it again.

The Error Center supports severity, status, marketplace, and code filtering. Resolution creates an audit event and retains the original issue.
