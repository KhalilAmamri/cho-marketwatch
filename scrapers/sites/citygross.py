from scrapers.scraper_base import scrape_products as scrape_products_base


COOKIE_SELECTORS = [
    "#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll",
    "#CybotCookiebotDialogBodyButtonAccept",
    "button:has-text('Till\u00e5t alla')",
    "button:has-text('Tillat alla')",
    "button:has-text('Till\u00e5t urval')",
]

AD_SELECTORS = [
    "[aria-label='Close']",
    ".modal-close",
    ".close",
]


def scrape_products(website_name="Citygross"):
    scrape_products_base(
        website_name,
        cookie_selectors=COOKIE_SELECTORS,
        ad_selectors=AD_SELECTORS,
    )

if __name__ == "__main__":
    scrape_products("Citygross")
