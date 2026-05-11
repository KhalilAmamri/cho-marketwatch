from scrapers.scraper_base import scrape_products as scrape_products_base


COOKIE_SELECTORS = [
    "role=button[name='Acceptera alla cookies']",
    "text=Acceptera alla cookies",
    "role=button[name='Accept all cookies']",
    "text=Accept all cookies",
    "button:has-text('Acceptera alla cookies')",
]

AD_SELECTORS = [
    "#cmpbox button[aria-label='Close']",
    "[aria-label='Close']",
    ".modal-close",
    ".close",
]


def scrape_products(website_name="Coop", product_url_id=None, headless_override=None):
    return scrape_products_base(
        website_name,
        cookie_selectors=COOKIE_SELECTORS,
        ad_selectors=AD_SELECTORS,
        product_url_id=product_url_id,
        headless_override=headless_override,
    )

if __name__ == "__main__":
    scrape_products("Coop")
