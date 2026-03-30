import re
from bs4 import BeautifulSoup

def parse_kesko_price(html):
    """Parse price from Kesko (Finland) HTML."""
    soup = BeautifulSoup(html, "html.parser")


    price_span = soup.find("span", attrs={"data-testid": "product-price"})
    if price_span:
        text = price_span.get_text()
        price_match = re.search(r"(\d+[.,]?\d*)", text)
        if price_match:
            price_str = price_match.group(1).replace(",", ".")
            return price_str, "EUR"

    return None
