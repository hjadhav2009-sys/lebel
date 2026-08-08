# Label overflow rules

Renderers measure in printer dots using the profile DPI. Flipkart tries the approved font-size ladder in order, wraps only within the text zone, and accepts the largest size whose complete required content fits. It never truncates, overlaps the protected barcode zone, or silently omits required fields.

Failures use stable codes such as `LABEL_TEXT_OVERFLOW`, `MISSING_REQUIRED_FIELD`, `MISSING_DIMENSIONS`, `FONT_NOT_AVAILABLE`, and `INVALID_LAYOUT_PROFILE`. Diagnostics record available and required heights, selected size, zones, format, and line. Operators correct data/profile settings and recompile; they do not bypass overflow for bulk jobs.
