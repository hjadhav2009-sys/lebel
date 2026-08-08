# Print transport state machine

`ready → rendering → artifact_ready → waiting_for_agent → claimed → spooling → spooled → completed` is the successful path. Rendering failures become `render_failed`; failures known to occur before acceptance become `transport_failed`. A failure after Windows may have accepted bytes becomes `uncertain`.

Prepared is not Rendered. Rendered is not Spooled. Spooled does not guarantee a physical label exited the printer. Uncertain is not safe to auto-retry: an operator must inspect the Windows queue and physical output before creating an exact reprint.

Claims use a short lease and secret claim token. Only the assigned agent may download or report. Expired claims can be reclaimed only before spooling; no automatic reclaim occurs from `spooling`, `spooled`, or `uncertain`.
