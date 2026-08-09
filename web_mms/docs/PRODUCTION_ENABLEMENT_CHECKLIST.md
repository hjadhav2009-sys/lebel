# Production enablement checklist

- Phase 3.1 CI and review pass.
- Local auth, named users, least-privilege roles, strong secret, secure cookie, and HTTPS exist.
- Paired agent is current; printer is `ready` with no unresolved error.
- Profile DPI/media/layout/font identity is read back.
- Non-simulation physical tests and server-derived scans pass.
- Exact approvals exist and are not revoked.
- Operators understand CI is not approval and spooled is not guaranteed output.
- Only then enable controlled server and agent transport flags.

Repository defaults remain `MMS_PRINT_TRANSPORT_ENABLED=false` and `MMS_ENABLE_PRINT_SIMULATION=false`.

