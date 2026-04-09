from scrapers.scraper_base import scrape_products as scrape_products_base


COOKIE_SELECTORS = [
    "#onetrust-accept-btn-handler",
    "button:has-text('Godkänn kakor')",
    "button:has-text('Godkann kakor')",
    "button:has-text('Godkänn')",
    "button:has-text('Godkann')",
]

AD_SELECTORS = [
    "[aria-label='Close']",
    ".modal-close",
    ".close",
]


def scrape_products(website_name="Ica"):
    scrape_products_base(
        website_name,
        cookie_selectors=COOKIE_SELECTORS,
        ad_selectors=AD_SELECTORS,
    )

if __name__ == "__main__":
    scrape_products("Ica")
