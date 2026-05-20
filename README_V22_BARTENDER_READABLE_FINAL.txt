V22 Tool 2 final update

What changed:
1. Tool 2 now has a visible PRN Print Mode dropdown on the Generate Labels screen.
   Options:
   - bartender_readable: daily recommended production print.
   - full_info_compact: extra info but smaller text.

2. bartender_readable now prints lower contact block from Branch Settings:
   Manufactured by / Marketed by:
   Short branch/business line
   Short address line(s)
   Customer Care mobile
   Email ID

3. Barcode PRN command was NOT changed, because the scanning barcode was already working.

4. Extra product fields are allowed in Format Mapping, but bartender_readable only prints what fits clearly.
   This prevents overlap and keeps final PRN label practical on 50mm x 50mm labels.

How to use Tool 2:
- Open Tool 2.
- Choose PRN Print Mode = bartender_readable.
- Check Branches & Settings: keep address short, set phone/email.
- Upload Excel/CSV.
- Select Printer.
- Generate PRN & Print.

Important: PDF is preview only. PRN/direct print is the final proof for thermal labels.
