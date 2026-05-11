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


def _get_product_url_target(product_url_id):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    pu.id,
                    pu.is_active,
                    w.site_name,
                    w.country
                FROM product_urls pu
                JOIN websites w ON pu.website_id = w.id
                WHERE pu.id = %s
                """,
                (int(product_url_id),),
            )
            return cursor.fetchone()


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


def run_single_product_url(product_url_id, headless_override=None):
    target = _get_product_url_target(product_url_id)
    if not target:
        raise LookupError("Product URL not found")

    target_id, is_active, site_name, country = target
    if not is_active:
        raise ValueError("Product URL is inactive")

    scraper = SCRAPER_HANDLERS.get(str(site_name).strip().lower())
    if not scraper:
        raise ValueError(f"No scraper implementation for website '{site_name}'")

    country_label = country or "Unknown"
    print(f"Running targeted scrape for product_url_id={target_id} ({site_name} / {country_label})")

    results = scraper(site_name, product_url_id=int(target_id), headless_override=headless_override)
    if not results:
        raise RuntimeError("Targeted scrape finished without result rows")

    return results[0]
