from scrapers.sites.coop import scrape_products as scrape_coop
from scrapers.sites.ica import scrape_products as scrape_ica
from scrapers.sites.kesko import scrape_products as scrape_kesko
from scrapers.sites.sok import scrape_products as scrape_sok
from scrapers.sites.citygross import scrape_products as scrape_citygross
from database.database_config import get_connection


SCRAPER_HANDLERS = {
    "coop": scrape_coop,
    "ica": scrape_ica,
    "citygross": scrape_citygross,
    "kesko": scrape_kesko,
    "sok": scrape_sok,
}


def _get_active_websites():
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT DISTINCT w.site_name, w.country
                FROM product_urls pu
                JOIN websites w ON pu.website_id = w.id
                WHERE pu.is_active = TRUE
                ORDER BY w.country NULLS LAST, w.site_name
                """
            )
            return cursor.fetchall()


def run_all_scrapers():
    websites = _get_active_websites()
    if not websites:
        print("⚠️ No active website URLs found in database. Nothing to scrape.")
        return

    ran_any = False
    for idx, (site_name, country) in enumerate(websites):
        scraper = SCRAPER_HANDLERS.get(str(site_name).strip().lower())
        if not scraper:
            print(f"⚠️ No scraper implementation for website '{site_name}'. Skipping.")
            continue

        if idx > 0:
            print()
        country_label = country or "Unknown"
        print(f"🌍 Country: {country_label}")
        scraper(site_name)
        ran_any = True

    if not ran_any:
        print("⚠️ No supported active websites found. Add product URLs for supported scrapers.")
