# Flipkart Consignment Matching

Flipkart quantity files are detected by headers, including FSN, SKU/SKU Id, Quantity Sent, Quantity, Qty Sent, and Qty. Quantity must be a positive integer and is the label Print Quantity—not catalog stock or pack size.

Matching is account-scoped and ordered:

1. Exact FSN + SKU pair.
2. FSN alone only when unique.
3. SKU alone only when unique.
4. Otherwise unmatched or `AMBIGUOUS_FSN_SKU_MATCH`.

The exact pair is attempted before checking FSN ambiguity, so F1/S1 and F1/S2 both match correctly. Matched category supplies the initial label format.
