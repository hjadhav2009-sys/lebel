# Flipkart hybrid renderer

`flipkart_hybrid_tspl_v1` rasterizes measured product text with an explicitly configured TrueType font and emits the FSN/listing barcode as native TSPL Code 128. It supports key chain, pendant/locket, bangle/bracelet/armlet, earring, jewellery set, necklace/chain, and car hanging ornament field orders plus Net Quantity, Dimensions, MRP, and Generic Name.

The barcode zone is protected from raster text. Missing dimensions, font, required values, invalid barcode content, or overflow blocks compilation. The initial version is experimental until each format/profile/DPI combination passes physical barcode scanning and is approved.
