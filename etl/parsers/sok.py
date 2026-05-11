import re
from bs4 import BeautifulSoup

# Regex to find price numbers (handles 1.95 and 1,95)
PRICE_NUMBER_RE = re.compile(r"(\d+(?:[\.,]\d{1,2})?)")

# Regex to find bundle deals: e.g., "2 pcs = €2.95" or "2 kpl = 2,95 €"
# Captures: Group 1 (Quantity), Group 2 (Total Price)
BUNDLE_RE = re.compile(r"(\d+)\s*(?:pcs|kpl)\s*=\s*€?\s*(\d+(?:[\.,]\d{1,2})?)")


def get_number(text: str | None) -> float | None:
    """Extracts a clean float from price strings, converting commas to dots."""
    if not text:
        return None

    clean_text = text.replace("€", "").replace("\xa0", " ").strip()
    match = PRICE_NUMBER_RE.search(clean_text)

    if match:
        value = match.group(1).replace(",", ".")
        try:
            return round(float(value), 2)
        except ValueError:
            return None
    return None


def get_last_number(text: str | None) -> float | None:
    """Extracts the last numeric token from text, useful for '30-day price' labels."""
    if not text:
        return None

    clean_text = text.replace("€", "").replace("\xa0", " ").strip()
    matches = PRICE_NUMBER_RE.findall(clean_text)
    if not matches:
        return None

    value = matches[-1].replace(",", ".")
    try:
        return round(float(value), 2)
    except ValueError:
        return None


def parse_sok_price(html: str):
    """
    Parses S-Kaupat HTML. Handles normalization of multi-buy bundles
    to ensure the current_price reflects the best available unit price.
    """
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")
    container = soup.find("div", {"data-test-id": "main-product-card"}) or soup

    # 1. Get the standard price for a single unit
    display_node = container.find(attrs={"data-test-id": "display-price"})
    single_unit_price = get_number(display_node.get_text(strip=True)) if display_node else None

    # 2. Get the Base Price (Lowest 30-day price for EU Omnibus compliance)
    base_price = None
    lowest_30_node = container.find(attrs={"data-test-id": "lowest-30-day-price"})

    if lowest_30_node:
        # Use the last number because labels often include "30" before the actual price.
        base_price = get_last_number(lowest_30_node.get_text(" ", strip=True))

    # Fallback: if no 30-day low exists, the single unit price is the base price
    if base_price is None:
        base_price = single_unit_price

    # 3. Handle Multi-buy Promotions (Normalization)
    # We look for labels like "2 pcs = €2.95" to see if buying more is cheaper
    current_price = single_unit_price

    labels = container.find_all("span", {"data-test-id": "product-label"})
    for label in labels:
        label_text = label.get_text(strip=True)
        bundle_match = BUNDLE_RE.search(label_text)

        if bundle_match:
            quantity = int(bundle_match.group(1))
            total_bundle_price = float(bundle_match.group(2).replace(",", "."))

            # Normalize: Calculate the price per single piece in the bundle
            normalized_bundle_price = round(total_bundle_price / quantity, 2)

            # If the bundle unit price is cheaper than the single unit price, use it
            if current_price is None or normalized_bundle_price < current_price:
                current_price = normalized_bundle_price
            break

    if current_price is None:
        return None

    # Keep return values consistent with other parsers.
    if base_price is None or base_price <= 0:
        base_price = current_price

    is_discounted = current_price < base_price

    return {
        "current_price": current_price,
        "base_price": base_price,
        "is_discounted": is_discounted,
        "currency": "EUR",
    }
