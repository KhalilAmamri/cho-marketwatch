from scrapers.scraper_base import scrape_products as scrape_products_base


COOKIE_SELECTORS = [
    "button[data-testid='uc-accept-all-button']",
    "button[data-testid='uc-accept-button']",
    "button:has-text('Hyväksy kaikki')",
    "button:has-text('Hyvaksy kaikki')",
    "button:has-text('Salli kaikki')",
    "button:has-text('Hyväksy')",
    "button:has-text('Hyvaksy')",
]

AD_SELECTORS = [
    "button:has-text('Sulje')",
    "[aria-label='Close']",
    ".modal-close",
    ".close",
]


def scrape_products(website_name="Sok"):
    scrape_products_base(
        website_name,
        cookie_selectors=COOKIE_SELECTORS,
        ad_selectors=AD_SELECTORS,
    )

if __name__ == "__main__":
    scrape_products("Sok")
