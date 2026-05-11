import re
from bs4 import BeautifulSoup

# Regular expression to extract the price number from a string
PRICE_NUMBER_RE = re.compile(r"(\d+(?:[\.,:]\d{1,2})?)")


def get_number(text: str | None) -> float | None:
    """Safely extracts and converts a price string into a float."""
    if not text:
        return None

    # Clean non-breaking spaces and html entities
    clean_text = str(text).replace("\xa0", " ").replace("&nbsp;", " ")

    # Fix: correct regex variable name
    match = PRICE_NUMBER_RE.search(clean_text)

    if match:
        # Normalize comma/colon to dot for float conversion
        value = match.group(1).replace(",", ".").replace(":", ".")
        try:
            return round(float(value), 2)
        except ValueError:
            return None
    return None


def parse_ica_price(html):
    """Parses ICA product pricing and handles normal, discount, and multi-buy cases."""
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")

    # Remove non-visible or styling elements to clean the document
    for element in soup(["script", "style", "nav", "footer", "noscript"]):
        element.decompose()

    # Locate the main product container on the page
    container = (
        soup.find("div", class_=re.compile(r"bfMttO|_box_1gkco_1"))
        or soup.find("div", class_="_grid-item-12_tilop_45")
        or soup
    )

    current_price = None
    base_price = None

    # --- CASE 1 & 2: Normal Price & Standard Discount ---
    price_container = container.find(attrs={"data-test": "price-container"})
    if price_container:
        main_price_text = price_container.get_text(strip=True)
        current_price = get_number(main_price_text)

        # Check if there's a strikethrough original price (discount)
        original_node = price_container.find(attrs={"data-test": "bop-price-original"})
        if original_node:
            base_price = get_number(original_node.get_text(strip=True))

    # --- CASE 3: Multi-item Promotions (e.g., 2 för 44 kr) ---
    promo_card = soup.find(attrs={"data-test": "offer-card-promotion"})
    promo_text = ""

    if promo_card:
        promo_text = promo_card.get_text(strip=True)
    else:
        # Fallback if promotion card is not located in container
        for text_node in container.find_all(text=True):
            txt = str(text_node).strip()
            lower_txt = txt.lower()
            if "för" in lower_txt or "for" in lower_txt:
                if len(txt) < 100:
                    promo_text = txt
                    break

    # Calculate unit price for the multi-item deal
    if promo_text and ("för" in promo_text.lower() or "for" in promo_text.lower()):
        numbers = re.findall(r"\d+", promo_text)
        if len(numbers) >= 2:
            try:
                qty = float(numbers[0])
                total_amt = float(numbers[1])
                if qty > 0:
                    promo_unit_price = round(total_amt / qty, 2)

                    # Update prices if the promotion is cheaper than the current price
                    if current_price is None or promo_unit_price < current_price:
                        if base_price is None or base_price == current_price:
                            base_price = current_price
                        current_price = promo_unit_price
                    elif base_price is None or base_price == current_price:
                        current_price = promo_unit_price
            except Exception:
                pass

    # --- FALLBACK: Reference price for discounts (30-day price) ---
    if base_price is None:
        ref_price_node = container.find(string=re.compile(r"30\s*dgr\s*pris", re.IGNORECASE))
        if ref_price_node:
            base_price = get_number(ref_price_node)

    # If no base price exists, set it equal to current price
    if base_price is None or base_price <= 0:
        base_price = current_price

    # Ensure a valid current price
    if current_price is None or current_price <= 0:
        return None

    is_discounted = current_price < base_price

    return {
        "current_price": current_price,
        "base_price": base_price,
        "is_discounted": is_discounted,
        "currency": "SEK",
    }
