V21 Tool 2 important fix

Problem found:
PDF preview and PRN print were different layouts. PDF looked good, but real PRN print became tiny.

Fix:
Tool 2 PRN is now treated as the real source-of-truth for thermal printing.
Default PRN mode is bartender_readable, which restores the working BarTender PRN values:
- TEXT font multipliers closer to original BarTender PRN
- 16-dot line spacing
- Code39 barcode command unchanged
- barcode text multiplier restored

Branch setting added:
prn_layout_mode = bartender_readable
Recommended for readable print and barcode scan.

Alternative:
prn_layout_mode = full_info_compact
This prints more address/customer-care information but text becomes smaller. Use only if required.

For final printing use Generate PRN & Print, not PDF.
