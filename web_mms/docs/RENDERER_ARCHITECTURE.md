# Renderer architecture

Renderers consume only immutable `PrintJobLine.data_snapshot` values and an explicit versioned printer profile. They expose validate, render, and preview operations. Output bytes, SHA-256, renderer key/version, layout version, profile, diagnostics, and creation actor are persisted in `PrintArtifact`.

The registry currently contains Amazon dynamic TSPL and Flipkart hybrid TSPL. Preview and production share measurement and placement helpers. Compilation is idempotent for a job/renderer/version/layout/profile tuple. Exact reprint copies historical snapshots; unavailable historical renderer/profile versions block rather than silently using current data.

Adapter protocols reserve future external renderer support without adding commercial dependencies.
