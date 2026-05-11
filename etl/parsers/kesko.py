import re
from bs4 import BeautifulSoup

# Regex to extract numeric values (handles both dot and comma decimals)
PRICE_NUMBER_RE = re.compile(r"(\d+(?:[\.,:]\d{1,2})?)")


def get_number(text: str | None) -> float | None:
    """
    Cleans a string and extracts the first valid number as a float.
    Converts European comma decimals (0,59) to standard dots (0.59).
    """
    if not text:
        return None

    # Replace non-breaking spaces and common HTML entities
    clean_text = text.replace("\xa0", " ").replace("&nbsp;", " ")
    match = PRICE_NUMBER_RE.search(clean_text)

    if match:
        # Standardize the decimal separator
        value = match.group(1).replace(",", ".").replace(":", ".")
        try:
            return round(float(value), 2)
        except ValueError:
            return None
    return None


def parse_kesko_price(html: str):
    """
    Parses product pricing from K-Ruoka (Kesko) HTML.
    Specifically handles 'Multi-buy' promotions (e.g., 4 for 2.00 EUR)
    by normalizing them to a single-unit price.
    """
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")

    # 1. Cleanup: Remove scripts and styles to avoid false positives during text extraction
    for element in soup(["script", "style", "nav", "footer", "noscript"]):
        element.decompose()

    # 2. Scope: Target the specific sidebar container where price info lives
    container = soup.find("div", {"data-testid": "product-details-sidebar"}) or soup

    current_price = None
    base_price = None
    quantity = 1.0  # Default to 1 piece if no multi-buy is found

    # 3. Extract Current Price (often inside a grid for integer/decimal parts)
    price_grid = container.find(attrs={"data-testid": "product-main-price-grid"})

    if price_grid:
        # Kesko splits prices into IntegerPart (e.g., '2') and DecimalPart (e.g., '00')
        integer_node = price_grid.find(class_=re.compile(r"IntegerPart"))
        decimal_node = price_grid.find(class_=re.compile(r"DecimalPart"))
        extra_node = price_grid.find(class_=re.compile(r"Extra"))  # Contains quantity info like '/4 pcs'

        if integer_node and decimal_node:
            combined_price_text = f"{integer_node.get_text(strip=True)}.{decimal_node.get_text(strip=True)}"
            current_price = get_number(combined_price_text)

        # 4. Handle Multi-buy Quantity
        # If the 'Extra' node contains a quantity (e.g., '/4'), we extract the '4'
        if extra_node:
            extra_text = extra_node.get_text(strip=True)
            qty_match = re.search(r"/(\d+)", extra_text)
            if qty_match:
                quantity = float(qty_match.group(1))

    # 5. Normalize Current Price to "Per Piece"
    # Example: If price is 2.00 and quantity is 4, new current_price becomes 0.50
    if current_price is not None and quantity > 1:
        current_price = round(current_price / quantity, 2)

    # 6. Extract Base Price (Standard price without Plussa card/promotion)
    # Kesko labels this as 'product-normal-price'
    normal_price_node = container.find(attrs={"data-testid": "product-normal-price"})
    if normal_price_node:
        # Usually contains text like: "Without Plussa card 0.59/piece"
        base_price = get_number(normal_price_node.get_text(strip=True))

    # 7. Final Logic & Validation
    # If no base price is found, the product is likely not on sale (Current = Base)
    if base_price is None or base_price <= 0:
        base_price = current_price

    if current_price is None:
        return None

    return {
        "current_price": current_price,
        "base_price": base_price,
        "is_discounted": current_price < base_price,
        "currency": "EUR",
    }
