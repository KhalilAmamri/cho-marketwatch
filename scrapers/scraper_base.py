import time
import random
import os
from datetime import datetime
from playwright.sync_api import sync_playwright
from scrapers._config import SCRAPING_CONFIG
from scrapers._utils import get_connection, get_product_urls, insert_raw_staging


def _slugify(value):
    slug = "".join(ch.lower() if ch.isalnum() else "_" for ch in str(value))
    slug = "_".join(filter(None, slug.split("_")))
    return slug or "site"


def _build_screenshot_name(product_url_id):
    # Human-readable filename: HH-MM-SS_id<product_url_id>.png
    time_part = datetime.now().strftime("%H-%M-%S")
    return f"{time_part}_id{product_url_id}.png"


def _try_click_locator(locator, timeout_ms=1200):
    try:
        match_count = locator.count()
    except Exception:
        return False

    for idx in range(match_count):
        target = locator.nth(idx)
        try:
            if not target.is_visible(timeout=timeout_ms):
                continue

            try:
                target.click(timeout=timeout_ms)
            except Exception:
                # Some CMP overlays require force click even when visible.
                target.click(timeout=timeout_ms, force=True)
            return True
        except Exception:
            continue

    return False


def _click_selectors_in_frame(frame, selectors, timeout_ms=1200):
    for selector in selectors or []:
        try:
            if _try_click_locator(frame.locator(selector), timeout_ms=timeout_ms):
                return True
        except Exception:
            continue
    return False


def _dismiss_overlays(page, cookie_selectors=None, ad_selectors=None, max_rounds=3):
    cookie_pool = list(cookie_selectors or [])
    ad_pool = list(ad_selectors or [])

    if not cookie_pool and not ad_pool:
        return

    for round_index in range(max_rounds):
        clicked = False

        if _click_selectors_in_frame(page, cookie_pool):
            clicked = True
        if _click_selectors_in_frame(page, ad_pool):
            clicked = True

        for frame in page.frames:
            if _click_selectors_in_frame(frame, cookie_pool):
                clicked = True
            if _click_selectors_in_frame(frame, ad_pool):
                clicked = True

        # Some banners close asynchronously.
        if clicked:
            page.wait_for_timeout(300)
        else:
            # Some sites mount cookie banners late after the initial network idle.
            if round_index < max_rounds - 1:
                page.wait_for_timeout(350)


def scrape_products(
    website_name,
    prepare_page=None,
    cookie_selectors=None,
    ad_selectors=None,
    product_url_id=None,
    headless_override=None,
):
    delay       = SCRAPING_CONFIG.get("delay_between_requests", 10)
    timeout     = SCRAPING_CONFIG.get("timeout", 30) * 1000
    max_retries = SCRAPING_CONFIG.get("max_retries", 2)
    configured_headless = SCRAPING_CONFIG.get("headless", True)
    headless = configured_headless if headless_override is None else bool(headless_override)
    save_screenshots = SCRAPING_CONFIG.get("save_screenshots", True)
    screenshot_full_page = SCRAPING_CONFIG.get("screenshot_full_page", True)
    screenshot_wait_ms = int(SCRAPING_CONFIG.get("screenshot_wait_ms", 700))
    screenshot_dir_cfg = SCRAPING_CONFIG.get("screenshot_dir", "storage/screenshots")
    operation_results = []

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    screenshot_root = os.path.join(project_root, screenshot_dir_cfg)
    website_screenshot_dir = os.path.join(
        screenshot_root,
        _slugify(website_name),
        datetime.now().strftime("%Y-%m-%d"),
    )
    if save_screenshots:
        os.makedirs(website_screenshot_dir, exist_ok=True)

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

                urls = get_product_urls(cursor, website_name, product_url_id=product_url_id)
                if not urls:
                    if product_url_id is not None:
                        print(f"⚠️  No active URL found for '{website_name}' with product_url_id={product_url_id}.")
                    else:
                        print(f"⚠️  No active URLs found for '{website_name}'.")
                    return operation_results

                for url_index, url_row in enumerate(urls):
                    product_url_id, _product_variant_id, brand_name, category, range_name, fmt, packaging, url, _store_id, store_code = url_row
                    store_tag     = f" (store {store_code})" if store_code else ""
                    range_tag     = f" {range_name}" if range_name else ""
                    product_label = f"{brand_name} {category}{range_tag} {fmt} {packaging}{store_tag}"
                    print(f"\n🔍 Scraping: {product_label}")
                    print(f"   URL: {url}")

                    item_result = {
                        "product_url_id": int(product_url_id),
                        "website_name": str(website_name),
                        "product_label": product_label,
                        "url": str(url),
                        "status": "failed",
                        "http_status_code": None,
                        "error_message": None,
                        "screenshot_path": None,
                        "raw_staging_id": None,
                    }

                    context = browser.new_context(
                        user_agent=SCRAPING_CONFIG["user_agent"],
                        viewport={"width": 1920, "height": 1080},
                    )
                    page       = context.new_page()
                    success    = False
                    last_error = None
                    screenshot_path = None

                    for attempt in range(1, max_retries + 1):
                        try:
                            response    = page.goto(url, wait_until="networkidle", timeout=int(timeout))

                            if prepare_page:
                                prepare_page(page)
                            else:
                                _dismiss_overlays(page, cookie_selectors=cookie_selectors, ad_selectors=ad_selectors)

                            if save_screenshots and screenshot_wait_ms > 0:
                                page.wait_for_timeout(screenshot_wait_ms)

                            if not prepare_page:
                                # Run a final overlay pass just before capture to handle late cookie modals.
                                _dismiss_overlays(
                                    page,
                                    cookie_selectors=cookie_selectors,
                                    ad_selectors=ad_selectors,
                                    max_rounds=2,
                                )

                            if save_screenshots:
                                screenshot_name = _build_screenshot_name(product_url_id)
                                screenshot_abs_path = os.path.join(website_screenshot_dir, screenshot_name)
                                page.screenshot(path=screenshot_abs_path, full_page=screenshot_full_page)
                                screenshot_path = os.path.relpath(screenshot_abs_path, project_root).replace("\\", "/")

                            html        = page.content()
                            status_code = response.status if response else 200

                            inserted_raw_id = insert_raw_staging(
                                cursor,
                                product_url_id,
                                html,
                                "pending",
                                status_code,
                                None,
                                screenshot_path=screenshot_path,
                            )
                            conn.commit()
                            item_result["status"] = "pending"
                            item_result["http_status_code"] = status_code
                            item_result["error_message"] = None
                            item_result["screenshot_path"] = screenshot_path
                            item_result["raw_staging_id"] = inserted_raw_id
                            print(f"   ✅ Success! Status: {status_code}")
                            if screenshot_path:
                                print(f"   📸 Screenshot saved: {screenshot_path}")
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
                        inserted_raw_id = insert_raw_staging(
                            cursor,
                            product_url_id,
                            "",
                            "failed",
                            None,
                            last_error,
                            screenshot_path=screenshot_path,
                        )
                        conn.commit()
                        item_result["status"] = "failed"
                        item_result["http_status_code"] = None
                        item_result["error_message"] = last_error
                        item_result["screenshot_path"] = screenshot_path
                        item_result["raw_staging_id"] = inserted_raw_id
                        print("   ❌ All attempts failed.")

                    operation_results.append(item_result)

                    if url_index < len(urls) - 1:
                        wait_time = delay + random.uniform(-2, 3)
                        print(f"   ⏱️  Waiting {wait_time:.1f}s before next product...")
                        time.sleep(wait_time)

        browser.close()
    return operation_results