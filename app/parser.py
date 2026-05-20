import pdfplumber
import re


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def clean(text):
    if not text:
        return ""
    return re.sub(r'\s+', ' ', str(text)).strip()


def _extract_text(pdf_path):
    """Extract all text from all pages of PDF."""
    full_text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                full_text += t + "\n"
    return full_text


# ─────────────────────────────────────────────
# SHIP TO BLOCK
# ─────────────────────────────────────────────

def _parse_ship_to(text):
    """
    Extract ship-to name, address, phone from the top block.
    Amazon format:
        Ship to:
        <Name>
        <address line 1>
        ...
        Phone : XXXXXXXXXX
        Order ID: ...
    """
    name = ""
    address_lines = []
    phone = ""

    lines = [l.strip() for l in text.split("\n") if l.strip()]

    # Find "Ship to:" anchor
    ship_idx = None
    for i, line in enumerate(lines):
        if re.search(r'^ship\s+to\s*:?$', line, re.IGNORECASE):
            ship_idx = i
            break

    if ship_idx is None:
        # Try inline: "Ship to: Name"
        for i, line in enumerate(lines):
            m = re.match(r'ship\s+to\s*:\s*(.+)', line, re.IGNORECASE)
            if m:
                ship_idx = i
                name = clean(m.group(1))
                break

    if ship_idx is not None:
        start = ship_idx + 1
        for line in lines[start:]:
            # Stop conditions
            if re.search(r'^order\s+id\s*:', line, re.IGNORECASE):
                break
            if re.search(r'^thank\s+you', line, re.IGNORECASE):
                break
            if re.search(r'^delivery\s+address', line, re.IGNORECASE):
                break
            if re.search(r'https?://', line):
                break

            # Phone extraction
            phone_match = re.search(r'phone\s*:?\s*(\d{10,})', line, re.IGNORECASE)
            if phone_match:
                phone = phone_match.group(1)
                continue

            if not name:
                name = clean(line)
            else:
                address_lines.append(clean(line))

    return name, ", ".join(address_lines), phone


# ─────────────────────────────────────────────
# PRODUCT FROM DECLARATION LETTER SECTION
# ─────────────────────────────────────────────

def _parse_product(text):
    """
    Extract clean product name from the Declaration Letter section.
    That block contains the full product text without price columns mixed in.
    Pattern:
        I, <name>, have placed the order for
        Quantity  Product Details
        1  <ProductName line 1>
           <ProductName line 2>
        SKU: ...
    """
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    product_lines = []
    collecting = False

    for line in lines:
        if re.search(r'have placed the order for', line, re.IGNORECASE):
            collecting = True
            continue

        if collecting:
            # Skip table header row
            if re.search(r'^quantity\s+product\s+details', line, re.IGNORECASE):
                continue
            # Leading "1 ProductName..." — strip quantity digit
            m = re.match(r'^\d+\s+(.+)', line)
            if m:
                product_lines.append(m.group(1))
                continue
            # Stop conditions
            if re.search(r'^SKU\s*:', line, re.IGNORECASE):
                break
            if re.search(r'^Condition\s*:', line, re.IGNORECASE):
                break
            if re.search(r'^Order\s+Item\s+ID', line, re.IGNORECASE):
                break
            if re.search(r'^Customisations', line, re.IGNORECASE):
                break
            if re.search(r'hereby confirm', line, re.IGNORECASE):
                break
            # Continuation line (no leading digit)
            if product_lines and line:
                product_lines.append(line)

    if product_lines:
        return re.sub(r'\s+', ' ', " ".join(product_lines)).strip()

    # ── Fallback: table area (first section) ────────────
    collecting = False
    product_lines = []
    for line in lines:
        if re.search(r'quantity\s+product\s+details\s+unit\s+price', line, re.IGNORECASE):
            collecting = True
            continue
        if collecting:
            if re.match(r'^SKU\s*:', line, re.IGNORECASE):
                break
            if re.search(r'item\s+subtotal', line, re.IGNORECASE):
                break
            line_clean = re.sub(r'^\d+\s+', '', line)
            line_clean = re.sub(r'\s*\u20b9[\d,\.]+\s*$', '', line_clean).strip()
            if line_clean:
                product_lines.append(line_clean)

    return re.sub(r'\s+', ' ', " ".join(product_lines)).strip()


# ─────────────────────────────────────────────
# CUSTOMISATIONS
# ─────────────────────────────────────────────

def _parse_customisations(text):
    """Extract customisation block between 'Customisations:' and 'Grand total'."""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    custom_lines = []
    collecting = False

    for line in lines:
        if re.search(r'^customisations?\s*:?$', line, re.IGNORECASE):
            collecting = True
            continue

        if collecting:
            if re.search(r'grand\s+total', line, re.IGNORECASE):
                break
            if re.search(r'thanks\s+for\s+buying', line, re.IGNORECASE):
                break
            if re.search(r'amazon\.in\s+declaration', line, re.IGNORECASE):
                break
            if line:
                custom_lines.append(clean(line))

    return custom_lines


# ─────────────────────────────────────────────
# MAIN PARSER
# ─────────────────────────────────────────────

def extract_order_data(pdf_path):
    """
    Parse a single Amazon packing slip PDF and return structured order dict.
    """
    text = _extract_text(pdf_path)
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    data = {}

    # ── SHIP TO ──
    name, address, phone = _parse_ship_to(text)
    data['ship_name']    = name
    data['ship_address'] = address
    data['ship_phone']   = phone

    # ── ORDER ID ──
    # Pattern: "Order ID: 407-3756079-5397149" optionally followed by "Custom Order"
    m = re.search(r'Order\s+ID\s*:\s*([\d\-]+)', text, re.IGNORECASE)
    data['order_id'] = m.group(1) if m else ""

    # ── IS CUSTOM ──
    # Check "Custom Order" text anywhere
    data['is_custom'] = bool(re.search(r'custom\s+order', text, re.IGNORECASE))

    # ── ORDER DATE ──
    m = re.search(r'Order\s+Date\s*:\s*(.+)', text, re.IGNORECASE)
    data['order_date'] = clean(m.group(1)) if m else ""

    # ── SHIPPING SERVICE ──
    m = re.search(r'Shipping\s+Service\s*:\s*(.+)', text, re.IGNORECASE)
    data['shipping_service'] = clean(m.group(1)) if m else ""

    # ── SELLER NAME ──
    m = re.search(r'Seller\s+Name\s*:\s*(.+)', text, re.IGNORECASE)
    data['seller_name'] = clean(m.group(1)) if m else "Sujal Fashion Works"

    # ── GRAND TOTAL ──
    # Look for "Grand total: ₹xxx"
    m = re.search(r'Grand\s+total\s*:\s*(\u20b9[\d,\.]+)', text, re.IGNORECASE)
    data['grand_total'] = m.group(1) if m else ""

    # ── SKU ──
    m = re.search(r'SKU\s*:\s*(\S+)', text, re.IGNORECASE)
    data['sku'] = m.group(1) if m else ""

    # ── ASIN ──
    m = re.search(r'ASIN\s*:\s*(\S+)', text, re.IGNORECASE)
    data['asin'] = m.group(1) if m else ""

    # ── QUANTITY ──
    # The quantity table column is almost always 1 for Amazon individual slips.
    # Look for "1 " at start of product table row (the Quantity column value).
    qty = "1"
    m = re.search(r'Quantity\s+Product\s+Details.*?\n\s*(\d+)\s+', text, re.DOTALL | re.IGNORECASE)
    if m:
        qty = m.group(1)
    data['qty'] = qty

    # ── PRODUCT NAME ──
    product = _parse_product(text)

    # Strip the SKU if it got appended in product text (Amazon quirk)
    if data['sku'] and product.endswith(data['sku']):
        product = product[:-len(data['sku'])].strip()

    # Clean garbage phrases
    for garbage in [
        r'PM Amazon.*',
        r'Thank you.*',
        r'Delivery address.*',
        r'SKU:.*',
        r'ASIN:.*',
        r'Condition:.*',
        r'Order Item ID:.*',
    ]:
        product = re.sub(garbage, '', product, flags=re.IGNORECASE)

    data['product_name'] = clean(product)

    # ── CUSTOMISATIONS ──
    data['customisations'] = _parse_customisations(text)

    # ── FROM ADDRESS (fixed) ──
    data['from_address'] = "Shop F-10, First Floor, Amarante\nPlot No.04, Sector-9E, Kalamboli - 410218\nContact: 9594790929"

    return data