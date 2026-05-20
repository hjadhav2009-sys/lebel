V24 Category PRN Templates

What changed:
1. Tool 2 now includes the uploaded BarTender PRN templates for these categories:
   - Bangle Bracelet Armlet
   - Car Hanging Ornament
   - Earring
   - Jewellery Set
   - Key Chain
   - Necklace Chain
   - Pendant Locket
   - Ring

2. Barcode command is now taken from the uploaded category PRN profile.
   Most uploaded BarTender PRNs use:
   BARCODE x,y,"93",42,0,180,2,4,"FSN"
   This means Code 93, height 42 dots, rotation 180, narrow/wide 2/4.

3. New reference files are saved in:
   marketplace_v12/reference_templates/bartender_category_prn/

4. QC reference ZIPs are saved in:
   marketplace_v12/samples/uploaded_qc_references_all/

5. New/updated category mapping database:
   marketplace_v12/data/label_formats.json
   marketplace_v12/data/prn_category_profiles.json

Important:
- PRN/direct print is the real final print. PDF preview can differ.
- Do one real PRN test print before batch.
- Do not change barcode type/height/narrow/wide unless scanner/printer uncle confirms.
