from bs4 import BeautifulSoup



def parse_citygross_price(html):
    """Parse price from Citygross (Sweden) HTML using stable Schema.org meta tag."""
    soup = BeautifulSoup(html, "html.parser")

    try:
        meta_price = soup.find("meta", attrs={"itemprop": "price"})
        if meta_price and meta_price.get("content"):
            price_str = str(meta_price["content"]).replace(",", ".")
            return price_str, "SEK"
    except Exception:
        pass

    return None
