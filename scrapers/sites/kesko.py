from scrapers.scraper_base import scrape_products as scrape_products_base


COOKIE_SELECTORS = [
    "#onetrust-accept-btn-handler",
    "button:has-text('Hyväksy kaikki')",
    "button:has-text('Hyvaksy kaikki')",
    "button:has-text('Hyväksy')",
    "button:has-text('Hyvaksy')",
    "button:has-text('Salli kaikki')",
]

AD_SELECTORS = [
    "button:has-text('Sulje')",
    "[aria-label='Close']",
    ".modal-close",
    ".close",
]


def scrape_products(website_name="Kesko", product_url_id=None, headless_override=None):
    return scrape_products_base(
        website_name,
        cookie_selectors=COOKIE_SELECTORS,
        ad_selectors=AD_SELECTORS,
        product_url_id=product_url_id,
        headless_override=headless_override,
    )

if __name__ == "__main__":
    scrape_products("Kesko")
