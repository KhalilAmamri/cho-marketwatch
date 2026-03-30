import json
import re
from bs4 import BeautifulSoup

def parse_coop_price(html):
    """Parse price from Coop (Sweden) HTML using stable Schema.org JSON-LD."""
    soup = BeautifulSoup(html, "html.parser")

    try:
        # Find ALL JSON-LD scripts
        scripts = soup.find_all("script", type="application/ld+json")
        
        for script in scripts:
            if script and script.string:
                data = json.loads(script.string)
                
                # Check if it's a Product schema
                if data.get("@type") == "Product":
                    offers = data.get("offers")
                    if isinstance(offers, list):
                        offers = offers[0] if offers else None
                    if isinstance(offers, dict):
                        price = offers.get("price")
                        if price is not None:
                            price_str = str(price).replace(",", ".")
                            return price_str, "SEK"
    except Exception:
        pass

    return None
