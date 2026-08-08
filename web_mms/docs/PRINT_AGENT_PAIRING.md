# Print agent pairing

An operator generates a short-lived, single-use code in Printers & Agents. On the printing PC run `START_MMS_PRINT_AGENT.bat --pair CODE`. The server stores only hashes of pairing codes and agent tokens. The returned token is stored using Windows DPAPI when `pywin32` is available; it is never displayed again except for a six-character hint.

Pairing codes expire after ten minutes by default and cannot be reused. A machine cannot create a second active identity. Revocation immediately disables its token. Rotate a machine by revoking it, generating a new pairing code, and pairing again. Do not send codes or tokens through tickets or logs.
