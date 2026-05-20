V23 real PRN text visibility fix

What changed:
- Tool 2 actual PRN print layout was patched, not only PDF preview.
- Product information remains in readable BarTender-style ROMAN.TTF size.
- Manufactured / Marketed by block is now larger and bolder in real PRN print.
- Lower block prints only important lines in bartender_readable mode:
  1. Manufactured by / Marketed by:
  2. Business/marketed-by name
  3. Short address line 1
  4. Customer Care number
  5. Email ID
- Barcode command was NOT changed because scanning was working.

Important:
For Tool 2, judge final print by Generate PRN & Print. PDF preview is only preview/export.
