# Import mapping

## Header detection

The importer scans the first 20 rows. Amazon technical headers receive a much higher detection score than visible labels. When technical fields exist, aliases only fill missing mappings. Column letters and positions are never used.

Amazon mappings include:

| Normalized field | Preferred technical key / pattern | Alias examples |
|---|---|---|
| SKU | `contribution_sku#1.value` | SKU, Seller SKU, Merchant SKU |
| ASIN/product ID | `amzn1.volt.ca.product_id_value` | Product ID, ASIN |
| Brand | `brand[...]#1.value` | Brand |
| Title | `item_name[...]#1.value` | Title, Product Name |
| MRP | `purchasable_offer[...]maximum_retail_price[...]value_with_tax` | MRP, Maximum Retail Price |
| Main image | `main_product_image_locator[...]#1.media_location` | Main Image URL |
| Other images | `other_product_image_locator_1` through `_8` | — |

The three reference Amazon templates therefore merge safely even when columns move. `source_file`, `source_template`, `source_category`, and import ID retain provenance.

Flipkart maps Listing ID, FSN, SKU, MRP, FSP, brand, and category/format. FSN is first-class and yields `https://www.flipkart.com/product/p/itme?pid={FSN}`. Unmapped nonempty cells stay in extra attributes. No image page is scraped during bulk import.

## Incremental decisions

Each normalized row creates a business key and canonical hash. Missing stable identifiers are errors. New keys insert; identical hashes stay untouched; changed hashes update current fields and create field-level audit events. Products absent from a later file are never deleted. Raw input JSON is stored on every import row. Missing MRP stays null and never receives a guessed fallback.
