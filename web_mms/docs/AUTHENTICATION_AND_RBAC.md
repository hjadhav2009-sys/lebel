# Authentication and RBAC

`MMS_AUTH_MODE=development` explicitly supplies a development Admin identity. `MMS_AUTH_MODE=local` requires a named active database user and an HttpOnly, SameSite=Strict session cookie. Run `python scripts/bootstrap_admin.py` inside the backend environment to create the first Admin; the password is read interactively and is never stored in source.

Admin manages users, pairing, agents, and printer/layout profiles. Admin or QC performs test printing, barcode verification, diagnostics, and approval. Packing and Print Operator may prepare/compile approved production jobs, view the queue, confirm output, and request exact reprints. The backend enforces every permission and records authenticated actor IDs.

Real transport refuses startup unless local auth, a non-default secret of at least 32 characters, and secure cookies are configured.

