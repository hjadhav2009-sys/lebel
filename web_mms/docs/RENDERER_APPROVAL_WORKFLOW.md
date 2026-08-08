# Renderer approval workflow

1. Pair the printing PC and discover the exact Windows queue.
2. Create a profile with media, gap, DPI, darkness, speed, renderer, font, and offsets.
3. Prepare a test job (maximum two labels per selected line), compile it, and print on the target device.
4. Inspect alignment and all text, scan the printed barcode, and record the verification.
5. Complete the test job and approve the exact printer profile, renderer key/version, layout version, and optionally format.

Bulk compilation is blocked without approval. Editing a profile increments its layout version, so the prior approval no longer applies. Revocation is audited. Development may allow unapproved test prints, never unapproved bulk transport.
