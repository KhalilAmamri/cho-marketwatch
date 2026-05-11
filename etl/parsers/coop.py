import re
from bs4 import BeautifulSoup

# Regular expression to extract the first decimal number from a string
PRICE_NUMBER_RE = re.compile(r"(\d+(?:[\.,:]\d{1,2})?)")


def get_number(text: str | None) -> float | None:
    """Safely extracts and converts a price string into a float."""
    if not text:
        return None
    match = PRICE_NUMBER_RE.search(text)
    if match:
        value = match.group(1).replace(",", ".").replace(":", ".")
        try:
            return round(float(value), 2)
        except ValueError:
            return None
    return None


def parse_coop_price(html):
    """
    Parses Coop product pricing from HTML.
    Handles standard prices and multi-item promotions (e.g., 2 för 54 kr) accurately.
    """
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")

    # Remove non-visible or styling elements to clean the document
    for element in soup(["script", "style", "nav", "footer", "noscript"]):
        element.decompose()

    current_price = None
    base_price = None

    # Locate the main product article container
    container = soup.find("article")
    if not container:
        container = soup

    # 1. Extract the current price
    price_nodes = container.find_all(class_=re.compile(r"(n1OznkM1|slH8Imgo)"))
    for node in price_nodes:
        text = node.get_text(strip=True)
        lower = text.lower()
        
        # Check if it's a multi-item promotion deal text like "2 för 54 kr" or "2 for 54 kr"
        if "för" in lower or "for" in lower:
            numbers = re.findall(r'\d+', text)
            if len(numbers) >= 2:
                try:
                    quantity = float(numbers[0])
                    total_price = float(numbers[1])
                    if quantity > 0:
                        current_price = round(total_price / quantity, 2)
                        break
                except Exception:
                    pass
        elif "kr" in text.lower():
            current_price = get_number(text)
            if current_price is not None:
                break

    # If we didn't find price in the specific nodes above, try a more general scan
    if current_price is None:
        visible_texts = [s for s in container.stripped_strings if s]
        for text in visible_texts:
            lower = text.lower()
            # Check for multi-item promo in free text (handle both "för" Swedish and "for" English)
            if "för" in lower or "for" in lower:
                numbers = re.findall(r'\d+', text)
                if len(numbers) >= 2:
                    try:
                        qty = float(numbers[0])
                        tot = float(numbers[1])
                        if qty > 0:
                            current_price = round(tot / qty, 2)
                            break
                    except Exception:
                        pass
            # Otherwise check for 'kr' or 'pris' mentions
            if "kr" in lower or "pris" in lower:
                current_price = get_number(text)
                if current_price is not None:
                    break

    # 2. Extract the base price (e.g., Tidigare lägsta pris or Ordinarie pris)
    ts_vm = container.find(class_="_tsVm3Q7")
    if ts_vm:
        base_candidates = ts_vm.find_all(string=re.compile(r"(Tidigare|Ord\.|pris)", re.IGNORECASE))
        for bc in base_candidates:
            text = bc.parent.get_text(strip=True) if hasattr(bc, 'parent') else str(bc)
            
            # Make sure we don't accidentally capture "Jfr pris" (unit comparison text)
            if "jfr" not in text.lower() and ("pris" in text.lower() or "tidigare" in text.lower()):
                base_price = get_number(text)
                if base_price is not None:
                    break

    # 3. Fallback: if no base price exists, set it equal to the current price
    if base_price is None or base_price <= 0:
        base_price = current_price

    # 4. Ensure we have a valid current price
    if current_price is None or current_price <= 0:
        return None

    # Calculate discount state
    is_discounted = base_price > current_price

    return {
        "current_price": current_price,
        "base_price": base_price,
        "is_discounted": is_discounted,
        "currency": "SEK",
    }
