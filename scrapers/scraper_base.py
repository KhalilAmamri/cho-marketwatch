import time
import random
from playwright.sync_api import sync_playwright
from scrapers._config import SCRAPING_CONFIG
from scrapers._utils import get_connection, get_product_urls, insert_raw_staging


def scrape_products(website_name):
    delay       = SCRAPING_CONFIG.get("delay_between_requests", 10)
    timeout     = SCRAPING_CONFIG.get("timeout", 30) * 1000
    max_retries = SCRAPING_CONFIG.get("max_retries", 2)
    headless    = SCRAPING_CONFIG.get("headless", True)

    print(f"🏬 {website_name} Scraper")
    print(f"⏱️  Delay between products: {delay}s")
    print(f"🎯 Max retries per product: {max_retries}")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )

        with get_connection() as conn:
            with conn.cursor() as cursor:

                urls = get_product_urls(cursor, website_name)
                if not urls:
                    print(f"⚠️  No active URLs found for '{website_name}'.")
                    return

                for product_url_id, _product_format_id, brand_name, product_type, category, range_name, fmt, packaging, url, _store_id, store_code in urls:
                    store_tag     = f" (store {store_code})" if store_code else ""
                    range_tag     = f" {range_name}" if range_name else ""
                    product_label = f"{brand_name} {product_type} {category}{range_tag} {fmt} {packaging}{store_tag}"
                    print(f"\n🔍 Scraping: {product_label}")
                    print(f"   URL: {url}")

                    context = browser.new_context(
                        user_agent=SCRAPING_CONFIG["user_agent"],
                        viewport={"width": 1920, "height": 1080},
                    )
                    page       = context.new_page()
                    success    = False
                    last_error = None

                    for attempt in range(1, max_retries + 1):
                        try:
                            response    = page.goto(url, wait_until="networkidle", timeout=int(timeout))
                            html        = page.content()
                            status_code = response.status if response else 200

                            insert_raw_staging(cursor, product_url_id, html, "pending", status_code, None)
                            conn.commit()
                            print(f"   ✅ Success! Status: {status_code}")
                            success = True
                            break

                        except Exception as e:
                            last_error = str(e)
                            print(f"   ⚠️  Attempt {attempt}/{max_retries} failed: {last_error}")
                            if attempt < max_retries:
                                time.sleep(2 ** attempt)

                    page.close()
                    context.close()

                    if not success:
                        insert_raw_staging(cursor, product_url_id, "", "failed", None, last_error)
                        conn.commit()
                        print("   ❌ All attempts failed.")

                    wait_time = delay + random.uniform(-2, 3)
                    print(f"   ⏱️  Waiting {wait_time:.1f}s before next product...")
                    time.sleep(wait_time)

        browser.close()