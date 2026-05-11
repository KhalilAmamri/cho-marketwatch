import re
from bs4 import BeautifulSoup

# ============================================
# REGEX PATTERNS - Used to find price labels
# ============================================

# Match any number that might be a price: 12, 12.5, 12:50, 12,50
PRICE_NUMBER_RE = re.compile(r"(\d+(?:[\.,:]\d{1,2})?)")

# Match reference/base price labels: "30 dgr pris", "ord pris", "ordinarie pris"
BASE_PRICE_LABEL_RE = re.compile(r"\b(30\s*dgr\s*pris|ord\.?\s*pris|ordinarie\s*pris|word price)\b", re.IGNORECASE)

# Match current price label: any text with "pris" (Swedish for "price")
CURRENT_PRICE_LABEL_RE = re.compile(r"\bpris\b", re.IGNORECASE)


# ============================================
# HELPER FUNCTION 1: Extract a price number
# ============================================
def get_number(text: str | None) -> float | None:
    """
    Extract and return a price as a float from any text.
    Examples:
      "Pris 25:50" -> 25.5
      "2 för 109" -> 54.5 (price per unit)
      "30 dgr pris 30:00" -> 30.0
    """
    if not text:
        return None

    # Convert text to lowercase for easier matching
    lowered = text.lower()
    
    # SPECIAL CASE 1: Handle promotional quantity deals like "2 för 109"
    # (This means: 2 items for 109 SEK, so each costs 54.5 SEK)
    if "för" in lowered or "for" in lowered:
        # Find all numbers in the text
        numbers = re.findall(r"\d+", text)
        if len(numbers) >= 2:
            quantity = float(numbers[0])  # First number = quantity
            total_price = float(numbers[1])  # Second number = total price
            if quantity > 0:
                # Calculate price per single item
                return round(total_price / quantity, 2)

    # NORMAL CASE: Extract a single price number
    match = PRICE_NUMBER_RE.search(text)
    if match:
        value = match.group(1).replace(",", ".").replace(":", ".")
        
        # SPECIAL CASE 2: If the text contains "30 dgr pris" (reference price label),
        # we need to take the LAST number, not the first one (to avoid picking up the "30")
        # Example: "30 dgr pris 30:00" should return 30.0, not 30.0
        if "30" in lowered and "pris" in lowered:
            # Find all potential price numbers
            all_floats = re.findall(r"\d+(?:[\.,:]\d{1,2})?", text)
            if len(all_floats) > 1:
                try:
                    # Take the last (actual price) number
                    return round(float(all_floats[-1].replace(",", ".")), 2)
                except ValueError:
                    pass

        try:
            return round(float(value), 2)
        except ValueError:
            return None
    return None


# ============================================
# HELPER FUNCTION 2: Find price with a label
# ============================================
def _price_after_label(strings: list[str], label_re: re.Pattern[str], skip_match_re: re.Pattern[str] | None = None) -> float | None:
    """
    Search for a price that appears near a specific label.
    
    Example: Find "30:00" that comes after "30 dgr pris"
    - First, look in the same text node as the label
    - If not found, check the next 3 text nodes
    
    Can optionally skip certain labels to avoid conflicts.
    """
    for index, text in enumerate(strings):
        # Check if this text contains the label we're looking for
        if not label_re.search(text):
            continue
        
        # If we want to skip certain labels, check for that
        if skip_match_re and skip_match_re.search(text):
            continue

        # Try to extract a price from this same text node
        price = get_number(text)
        if price is not None:
            return price

        # If no price in the label text, check the next few text nodes
        for next_text in strings[index + 1 : index + 4]:
            price = get_number(next_text)
            if price is not None:
                return price
    return None


# ============================================
# HELPER FUNCTION 3: Extract promotional price
# ============================================
def extract_promo_price(strings: list[str]) -> float | None:
    """
    Handle quantity deals that might be split across multiple text nodes.
    
    Example:
      Node 1: "2 för"  (2 items for)
      Node 2: "109:-"  (109 SEK)
      Result: 54.5 (price per unit)
    """
    for index, text in enumerate(strings):
        lowered = text.lower()
        
        # Look for deal keywords: "för" (Swedish) or "for" (English)
        if "för" in lowered or "for" in lowered:
            # Extract all numbers from this text (find the quantity)
            quantity_numbers = re.findall(r"\d+", text)
            if not quantity_numbers:
                continue

            quantity = float(quantity_numbers[0])  # First number = quantity

            # Search next 3 text nodes for the actual price amount
            for next_text in strings[index + 1 : index + 4]:
                price = get_number(next_text)
                if price is not None and quantity > 0:
                    # Calculate price per single item
                    return round(price / quantity, 2)
    return None


# ============================================
# MAIN FUNCTION: Parse CityGross price HTML
# ============================================
def parse_citygross_price(html: str):
    """
    Main function to extract pricing data from CityGross HTML.
    
    Returns a dictionary with:
      - current_price: The price you pay today (may include promotion)
      - base_price: The regular/original price
      - is_discounted: Boolean - is there a discount applied?
      - currency: Always "SEK" for Swedish Krona
    """
    # Parse HTML using BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")

    # Find the main container that holds product information
    # Try different container class names, fall back to entire soup
    container = (
        soup.find("div", class_="product-single-container")
        or soup.find("div", class_="details-block")
        or soup
    )

    # Extract all text strings from the container, remove empty ones
    strings = [s for s in container.stripped_strings if s]

    # -------- STEP 1: Find the base/reference price --------
    # Look for labels like "30 dgr pris", "ord pris", etc.
    base_price = _price_after_label(strings, BASE_PRICE_LABEL_RE)

    # -------- STEP 2: Find the current price --------
    # Look for "pris" label, but skip if it's a base price label
    current_price = _price_after_label(strings, CURRENT_PRICE_LABEL_RE, skip_match_re=BASE_PRICE_LABEL_RE)
    
    # Also check for promotional quantity deals (like "2 för 109")
    promo_price = extract_promo_price(strings)

    # If we found a promo deal, use it as the current price
    if promo_price is not None:
        current_price = promo_price

    # -------- STEP 3: Fallback search if current price is still missing --------
    # Scan all text for "för" or "for" keywords as a last resort
    if current_price is None:
        for text in strings:
            lowered = text.lower()
            if any(marker in lowered for marker in ["för", "for"]):
                current_price = get_number(text)
                if current_price is not None:
                    break

    # -------- STEP 4: Validation - we MUST have a current price --------
    if current_price is None:
        return None  # No price found, return empty

    # -------- STEP 5: If base price is missing, use current price --------
    # This means there's no discount (same price as base price)
    if base_price is None or base_price <= 0:
        base_price = current_price

    # -------- STEP 6: Final validation - both prices must be positive --------
    if current_price <= 0 or base_price <= 0:
        return None  # Invalid prices

    # -------- SUCCESS: Return the pricing data --------
    return {
        "current_price": current_price,
        "base_price": base_price,
        "is_discounted": current_price < base_price,
        "currency": "SEK",
    }
