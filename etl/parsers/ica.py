import json
from bs4 import BeautifulSoup

def parse_ica_price(html):
    """Parse price from Ica (Sweden) HTML using JSON-LD structured data."""
    soup = BeautifulSoup(html, "html.parser")

    # Find JSON-LD script tag
    script_tag = soup.find("script", {"type": "application/ld+json", "data-rh": "true"})
    if script_tag:
        try:
            data = json.loads(script_tag.string)
            
            # Extract price from Offer object
            if isinstance(data, dict):
                offer = data.get("offers") or data.get("@type") == "Offer" and data
                if offer:
                    price = offer.get("price")
                    currency = offer.get("priceCurrency", "SEK")
                    if price:
                        return str(price), currency
        except (json.JSONDecodeError, AttributeError):
            pass

    return None
