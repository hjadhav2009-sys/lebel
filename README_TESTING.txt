M Men Style - Marketplace Label Generator V11 Advanced

MAIN FIXES IN V11
1. PDF generation now runs in background thread.
   - App should not show Not Responding when generating 100, 1000, or large label quantities.
   - Status bar shows progress every 100 labels.
2. Added large quantity safety.
   - Above 2,000 labels: software asks confirmation.
   - Above 20,000 labels: software blocks one huge PDF and asks you to split batches.
3. Quantity per SKU:
   - Select file.
   - Select SKU row.
   - Enter quantity in Print Qty box.
   - Click Apply Qty to Selected SKU.
   - Example: enter 100, then PDF repeats that SKU label 100 times.
   - Double-click SKU row for popup quantity entry.
4. Default PDF layout is now 2-column sticker roll.
5. Preview now fits inside screen better; PDF is the final reference.
6. Label font and spacing improved for 49.8mm x 49.8mm label.

PRINTING RULE
Use Actual Size / 100% / No Scaling.
For your sticker roll, keep PDF Layout = 2-column sticker roll.

TESTING STEPS
1. Run install_requirements.bat one time.
2. Run SELF_TEST.bat to confirm PDF generation.
3. Run run_app.bat.
4. Upload Flipkart CSV/XLSX files.
5. Select one file and select one SKU row.
6. Enter Print Qty, e.g. 10 or 100.
7. Click Apply Qty to Selected SKU.
8. Click Generate PDF.
9. For first physical test, print only 1 page.

DEBUG
If anything fails, run RUN_DEBUG.bat and send debug_log.txt plus screenshot.


V11 UPDATE:
- Improved 50mm label readability.
- Cleaner manufacturer/company block with less blank middle space.
- Wider barcode and clearer FSN text separation.
- PDF output name now uses v11.
- Quantity/background generation from V10 is kept.

Printing reminder:
Use 2-column sticker roll layout for your roll, and print with Actual Size / 100% / No Scaling.


V12 EXACT 2UP THERMAL ROLL SETTINGS
-----------------------------------
Use this version for your measured roll:
- Total roll / PDF page width: 106 mm
- Label height: 50 mm
- Left label width: 50 mm
- Middle gap: 3 mm
- Right label width: 50 mm
- Side margin auto/default: 1.5 mm each side
- Rows per PDF page: 1 row = 2 labels

In the software choose: PDF Layout = 2-column sticker roll.
In TSC TE244 printer Properties create/edit stock:
- Width: 106 mm
- Height: 50 mm
- Orientation: Portrait
In Adobe Acrobat print:
- Actual Size / 100%
- Fit OFF
- Shrink OFF
- Multiple OFF
Print only 1 page first for calibration.
