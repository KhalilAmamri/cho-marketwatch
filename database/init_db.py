# database/init_db.py
"""
Database initialization and seeding.
Loads all data from the company weekly historical CSV into the database.

Table order:
    websites → brands → categories → ranges → products → formats → packagings
    → product_variants → stores → product_urls
    → exchange_rates → weekly_price_summary
"""

import csv
from datetime import date, timedelta
import os
from urllib.parse import urlparse

from database.database_config import get_connection


# =============================================================================
# CONFIGURATION
# =============================================================================

CSV_TARGETS_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "olive_oil_historical_prices.csv")
)

CSV_HISTORICAL_FX_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "historical_fx.csv")
)

# Websites with implemented scrapers should be active after seeding.
SUPPORTED_SCRAPER_WEBSITES = {
    "citygross",
    "coop",
    "ica",
    "kesko",
    "sok",
}


# =============================================================================
# CSV
# =============================================================================

def load_csv_rows():
    if not os.path.exists(CSV_TARGETS_PATH):
        print(f"  ⚠️ CSV not found: {CSV_TARGETS_PATH}")
        return []
    with open(CSV_TARGETS_PATH, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_historical_fx_rows():
    if not os.path.exists(CSV_HISTORICAL_FX_PATH):
        print(f"  ⚠️ FX CSV not found: {CSV_HISTORICAL_FX_PATH}")
        return []
    with open(CSV_HISTORICAL_FX_PATH, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _parse_week_start(row):
    week_start = str(row.get("Week Start", "")).strip()
    if week_start:
        return week_start

    week_label = str(row.get("Week Label", "")).strip()
    if not week_label:
        return None

    parts = week_label.replace("Sem du ", "").split(" au ")
    if not parts:
        return None

    start_part = parts[0]
    try:
        day, month, year = start_part.split("-")
        return f"{year}-{month}-{day}"
    except ValueError:
        return None


def _parse_price(value):
    raw = str(value or "").strip().replace(",", ".")
    if not raw:
        return None
    try:
        return round(float(raw), 2)
    except ValueError:
        return None


def _parse_rate_to_eur(value):
    raw = str(value or "").strip().replace(",", ".")
    if not raw:
        return None
    try:
        parsed = float(raw)
        if parsed <= 0:
            return None
        return parsed
    except ValueError:
        return None


def _parse_volume(size_value):
    raw = str(size_value or "").strip().upper().replace(" ", "")
    if not raw:
        return None, None

    if raw.endswith("ML"):
        try:
            return round(float(raw[:-2]), 3), "ML"
        except ValueError:
            return None, None

    if raw.endswith("L"):
        try:
            return round(float(raw[:-1]), 3), "L"
        except ValueError:
            return None, None

    return None, None


def _seed_scraper_status(site_name):
    normalized = str(site_name or "").strip().lower()
    if normalized in SUPPORTED_SCRAPER_WEBSITES:
        return "active"
    return "pending"


# =============================================================================
# INSERT FUNCTIONS
# =============================================================================

def insert_websites(cursor, rows):
    print("\n📌 Inserting websites...")
    seen = {}
    for row in rows:
        site_name = row.get("Store", "").strip()
        country   = row.get("Country", "").strip()
        url       = row.get("Link", "").strip()

        if not site_name or site_name in seen:
            continue

        if not country:
            print(f"  ! Skipped website {site_name}: missing country")
            continue

        parsed   = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else ""
        if not base_url:
            print(f"  ! Skipped website {site_name}: missing or invalid base URL")
            continue

        scraper_status = _seed_scraper_status(site_name)
        seen[site_name] = True

        cursor.execute("SELECT id, base_url, country, scraper_status FROM websites WHERE site_name = %s", (site_name,))
        existing = cursor.fetchone()
        if existing:
            website_id, current_base_url, current_country, current_status = existing
            if (
                current_status != scraper_status
                or (current_base_url or "") != base_url
                or (current_country or "") != country
            ):
                cursor.execute(
                    "UPDATE websites SET base_url = %s, country = %s, scraper_status = %s WHERE id = %s",
                    (base_url, country, scraper_status, website_id),
                )
                print(f"  ✓ Updated website: {site_name} ({scraper_status})")
                continue
            print(f"  ✓ {site_name} already exists")
        else:
            cursor.execute(
                "INSERT INTO websites (site_name, base_url, country, scraper_status) VALUES (%s, %s, %s, %s)",
                (site_name, base_url, country, scraper_status)
            )
            print(f"  ✓ Inserted website: {site_name} ({scraper_status})")


def insert_brands(cursor, rows):
    print("\n📌 Inserting brands...")
    seen = set()
    for row in rows:
        brand = row.get("Brand", "").strip()
        if not brand or brand in seen:
            continue
        seen.add(brand)

        cursor.execute("SELECT id FROM brands WHERE brand_name = %s", (brand,))
        if cursor.fetchone():
            print(f"  ✓ {brand} already exists")
        else:
            cursor.execute("INSERT INTO brands (brand_name) VALUES (%s)", (brand,))
            print(f"  ✓ Inserted brand: {brand}")

def insert_categories(cursor, rows):
    print("\n📌 Inserting categories...")
    seen = set()
    for row in rows:
        category = row.get("Category", "").strip()
        if not category or category in seen:
            continue
        seen.add(category)
        cursor.execute("SELECT id FROM categories WHERE category_name = %s", (category,))
        if cursor.fetchone():
            print(f"  ✓ {category} already exists")
        else:
            cursor.execute("INSERT INTO categories (category_name) VALUES (%s)", (category,))
            print(f"  ✓ Inserted category: {category}")


def insert_ranges(cursor, rows):
    print("\n📌 Inserting ranges...")
    seen = set()
    for row in rows:
        range_name = row.get("Range", "").strip()
        if not range_name or range_name in seen:
            continue
        seen.add(range_name)
        cursor.execute("SELECT id FROM ranges WHERE range_name = %s", (range_name,))
        if cursor.fetchone():
            print(f"  ✓ {range_name} already exists")
        else:
            cursor.execute("INSERT INTO ranges (range_name) VALUES (%s)", (range_name,))
            print(f"  ✓ Inserted range: {range_name}")

def insert_products(cursor, rows):
    print("\n📌 Inserting products...")
    seen = set()
    for row in rows:
        brand        = row.get("Brand", "").strip()
        category     = row.get("Category", "").strip()
        range_name   = row.get("Range", "").strip()

        if not brand:
            continue

        key = (brand, category, range_name)
        if key in seen:
            continue
        seen.add(key)

        cursor.execute("SELECT id FROM brands WHERE brand_name = %s", (brand,))
        brand_row = cursor.fetchone()
        if not brand_row:
            print(f"  ⚠️ Brand not found: {brand}")
            continue

        cursor.execute("SELECT id FROM categories WHERE category_name = %s", (category,))
        cat_row = cursor.fetchone()
        if not cat_row:
            print(f"  ⚠️ Category not found: {category}")
            continue

        cursor.execute("SELECT id FROM ranges WHERE range_name = %s", (range_name,))
        range_row = cursor.fetchone()
        if not range_row:
            print(f"  ⚠️ Range not found: {range_name}")
            continue

        brand_id        = brand_row[0]
        category_id     = cat_row[0]
        range_id        = range_row[0]

        cursor.execute(
            "SELECT id FROM products WHERE brand_id = %s AND category_id = %s AND range_id = %s",
            (brand_id, category_id, range_id)
        )
        if cursor.fetchone():
            print(f"  ✓ {brand} {category} {range_name} already exists")
        else:
            cursor.execute(
                "INSERT INTO products (brand_id, category_id, range_id) VALUES (%s, %s, %s)",
                (brand_id, category_id, range_id)
            )
            print(f"  ✓ Inserted product: {brand} {category} {range_name}")

def insert_formats(cursor, rows):
    print("\n📌 Inserting formats...")
    seen = set()
    for row in rows:
        fmt = row.get("Size", "").strip().replace(" ", "").upper()
        volume_value, volume_unit = _parse_volume(row.get("Size", ""))
        if not fmt or fmt in seen:
            continue
        seen.add(fmt)

        cursor.execute("SELECT id FROM formats WHERE format_name = %s", (fmt,))
        if cursor.fetchone():
            print(f"  ✓ Format {fmt} already exists")
        else:
            if volume_value is None or volume_unit is None:
                print(f"  ⚠️ Skipped format {fmt}: could not parse volume")
                continue

            cursor.execute(
                "INSERT INTO formats (format_name, volume_value, volume_unit) VALUES (%s, %s, %s)",
                (fmt, volume_value, volume_unit),
            )
            print(f"  ✓ Inserted format: {fmt}")


def insert_packagings(cursor, rows):
    print("\n📌 Inserting packagings...")
    seen = set()
    for row in rows:
        packaging = row.get("Packaging", "").strip()
        if not packaging or packaging in seen:
            continue
        seen.add(packaging)

        cursor.execute("SELECT id FROM packagings WHERE packaging_name = %s", (packaging,))
        if cursor.fetchone():
            print(f"  ✓ Packaging {packaging} already exists")
        else:
            cursor.execute("INSERT INTO packagings (packaging_name) VALUES (%s)", (packaging,))
            print(f"  ✓ Inserted packaging: {packaging}")


def insert_product_variants(cursor, rows):
    print("\n📌 Inserting product variants...")
    seen = set()
    for row in rows:
        brand        = row.get("Brand", "").strip()
        category     = row.get("Category", "").strip()
        range_name   = row.get("Range", "").strip()
        fmt          = row.get("Size", "").strip().replace(" ", "").upper()
        packaging    = row.get("Packaging", "").strip()

        if not brand or not fmt or not packaging:
            continue

        key = (brand, category, range_name, fmt, packaging)
        if key in seen:
            continue
        seen.add(key)

        # Get product_id
        cursor.execute(
            """
            SELECT p.id FROM products p
                        JOIN brands b ON p.brand_id = b.id
                        JOIN categories c ON p.category_id = c.id
                        JOIN ranges r ON p.range_id = r.id
            WHERE b.brand_name = %s
              AND c.category_name = %s
              AND r.range_name = %s
            """,
            (brand, category, range_name)
        )
        product_row = cursor.fetchone()
        if not product_row:
            print(f"  ⚠️ Product not found: {brand} {category} {range_name}")
            continue
        product_id = product_row[0]

        cursor.execute("SELECT id FROM formats WHERE format_name = %s", (fmt,))
        format_row = cursor.fetchone()
        if not format_row:
            print(f"  ⚠️ Format not found: {fmt}")
            continue
        format_id = format_row[0]

        cursor.execute("SELECT id FROM packagings WHERE packaging_name = %s", (packaging,))
        packaging_row = cursor.fetchone()
        if not packaging_row:
            print(f"  ⚠️ Packaging not found: {packaging}")
            continue
        packaging_id = packaging_row[0]

        cursor.execute(
            "SELECT id FROM product_variants WHERE product_id = %s AND format_id = %s AND packaging_id = %s",
            (product_id, format_id, packaging_id)
        )
        if cursor.fetchone():
            print(f"  ✓ Variant {fmt} {packaging} already exists for {brand} {range_name}")
        else:
            cursor.execute(
                "INSERT INTO product_variants (product_id, format_id, packaging_id) VALUES (%s, %s, %s)",
                (product_id, format_id, packaging_id)
            )
            print(f"  ✓ Inserted variant: {brand} {category} {range_name} {fmt} {packaging}")


def insert_stores(cursor, rows):
    print("\n📌 Inserting stores...")

    cursor.execute("SELECT id, site_name FROM websites")
    websites = {row[1]: row[0] for row in cursor.fetchall()}

    for row in rows:
        site_name  = row.get("Store", "").strip()
        store_code = row.get("Store Code", "").strip()

        if not site_name or not store_code or store_code.lower() == "x":
            continue

        website_id = websites.get(site_name)
        if not website_id:
            print(f"  ⚠️ Website not found: {site_name}")
            continue

        cursor.execute(
            "SELECT id FROM stores WHERE website_id = %s AND store_code = %s",
            (website_id, store_code)
        )
        if cursor.fetchone():
            print(f"  ✓ Store {store_code} already exists for {site_name}")
        else:
            cursor.execute(
                "INSERT INTO stores (website_id, store_code) VALUES (%s, %s)",
                (website_id, store_code)
            )
            print(f"  ✓ Inserted store {store_code} for {site_name}")


def insert_product_urls(cursor, rows):
    print("\n📌 Inserting product URLs...")

    cursor.execute("SELECT id, site_name FROM websites")
    websites = {row[1]: row[0] for row in cursor.fetchall()}

    cursor.execute("SELECT id, website_id, store_code FROM stores")
    stores = {(row[1], row[2]): row[0] for row in cursor.fetchall()}

    for row in rows:
        site_name    = row.get("Store", "").strip()
        url          = row.get("Link", "").strip()
        brand        = row.get("Brand", "").strip()
        category     = row.get("Category", "").strip()
        range_name   = row.get("Range", "").strip()
        fmt          = row.get("Size", "").strip().replace(" ", "").upper()
        packaging    = row.get("Packaging", "").strip()
        store_code   = row.get("Store Code", "").strip()

        if not site_name or not url or not brand:
            continue

        website_id = websites.get(site_name)
        if not website_id:
            print(f"  ⚠️ Website not found: {site_name}")
            continue

        # Get store_id
        if not store_code or store_code.lower() == "x":
            store_id    = None
            store_label = ""
        else:
            store_id = stores.get((website_id, store_code))
            store_label = f" (store {store_code})"
            if not store_id:
                print(f"  ⚠️ Store not found: {site_name} store {store_code}")
                continue

        # Get product_variant_id
        cursor.execute(
            """
            SELECT pv.id FROM product_variants pv
            JOIN products p ON pv.product_id = p.id
            JOIN brands b ON p.brand_id = b.id
            JOIN categories c ON p.category_id = c.id
            JOIN ranges r ON p.range_id = r.id
            JOIN formats f ON pv.format_id = f.id
            JOIN packagings pk ON pv.packaging_id = pk.id
            WHERE b.brand_name = %s
              AND c.category_name = %s
              AND r.range_name = %s
              AND f.format_name = %s
              AND pk.packaging_name = %s
            """,
            (brand, category, range_name, fmt, packaging)
        )
        variant_row = cursor.fetchone()
        if not variant_row:
            print(f"  ⚠️ Variant not found: {brand} {category} {range_name} {fmt} {packaging}")
            continue
        product_variant_id = variant_row[0]

        # Check duplicate
        cursor.execute(
            "SELECT id FROM product_urls WHERE website_id = %s AND product_variant_id = %s AND store_id IS NOT DISTINCT FROM %s",
            (website_id, product_variant_id, store_id)
        )
        if cursor.fetchone():
            print(f"  ✓ URL already exists for {site_name}{store_label} - {brand} {category} {range_name} {fmt} {packaging}")
            continue

        cursor.execute(
            "INSERT INTO product_urls (website_id, store_id, product_variant_id, url) VALUES (%s, %s, %s, %s)",
            (website_id, store_id, product_variant_id, url)
        )
        print(f"  ✓ URL inserted for {site_name}{store_label} - {brand} {category} {range_name} {fmt} {packaging}")


def insert_exchange_rates(cursor, fx_rows):
    print("\n📌 Inserting historical exchange rates...")

    inserted = 0
    skipped = 0

    for row in fx_rows:
        currency = str(row.get("currency") or row.get("Currency") or "").strip().upper()
        fx_date = str(row.get("date") or row.get("Date") or "").strip()
        rate_to_eur = _parse_rate_to_eur(row.get("rate_to_eur") or row.get("Rate To EUR"))

        if not currency or not fx_date or rate_to_eur is None:
            skipped += 1
            continue

        cursor.execute(
            """
            INSERT INTO exchange_rates (currency, date, rate_to_eur)
            VALUES (%s, %s, %s)
            ON CONFLICT (currency, date)
            DO UPDATE SET rate_to_eur = EXCLUDED.rate_to_eur
            """,
            (currency, fx_date, rate_to_eur),
        )
        inserted += 1

    print(f"  ✓ Upserted exchange rate rows: {inserted}")
    print(f"  ℹ️ Skipped rows: {skipped}")


def _fill_missing_weeks_to_today(cursor):
    today = date.today()
    inserted = 0

    cursor.execute(
        """
        SELECT
            product_variant_id,
            website_id,
            store_id,
            MIN(week_start) AS min_week_start,
            (ARRAY_AGG(currency ORDER BY week_start DESC))[1] AS preferred_currency
        FROM weekly_price_summary
        GROUP BY product_variant_id, website_id, store_id
        """
    )
    scope_rows = cursor.fetchall()

    for product_variant_id, website_id, store_id, min_week_start, preferred_currency in scope_rows:
        if min_week_start is None:
            continue

        currency = str(preferred_currency or "EUR").upper()

        cursor.execute(
            """
            SELECT week_start
            FROM weekly_price_summary
                        WHERE product_variant_id = %s
              AND website_id = %s
              AND store_id IS NOT DISTINCT FROM %s
            """,
                        (product_variant_id, website_id, store_id),
        )
        existing_weeks = {week_row[0] for week_row in cursor.fetchall()}

        week_cursor = min_week_start
        while week_cursor <= today:
            if week_cursor not in existing_weeks:
                cursor.execute(
                    """
                    INSERT INTO weekly_price_summary
                    (
                        product_variant_id,
                        website_id,
                        store_id,
                        week_start,
                        avg_price,
                        sample_count,
                        currency,
                        data_status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        product_variant_id,
                        website_id,
                        store_id,
                        week_cursor,
                        None,
                        0,
                        currency,
                        "MISSING",
                    ),
                )
                inserted += 1

            week_cursor += timedelta(days=7)

    return inserted


def insert_weekly_price_summary(cursor, rows):
    print("\n📌 Inserting weekly price summary...")

    cursor.execute("SELECT id, site_name FROM websites")
    websites = {row[1]: row[0] for row in cursor.fetchall()}

    cursor.execute("SELECT id, website_id, store_code FROM stores")
    stores = {(row[1], row[2]): row[0] for row in cursor.fetchall()}

    inserted = 0
    updated = 0
    skipped = 0

    for row in rows:
        site_name = row.get("Store", "").strip()
        brand = row.get("Brand", "").strip()
        category = row.get("Category", "").strip()
        range_name = row.get("Range", "").strip()
        fmt = row.get("Size", "").strip().replace(" ", "").upper()
        packaging = row.get("Packaging", "").strip()
        store_code = row.get("Store Code", "").strip()
        price = _parse_price(row.get("Price", ""))
        currency = str(row.get("Currency", "")).strip().upper() or None
        week_start = _parse_week_start(row)

        if not site_name or not brand or not category or not range_name or not fmt or not packaging:
            skipped += 1
            continue

        if not week_start or not currency:
            skipped += 1
            continue

        data_status = "OK" if (price is not None and price > 0) else "MISSING"
        avg_price = price if data_status == "OK" else None
        sample_count = 1 if data_status == "OK" else 0

        website_id = websites.get(site_name)
        if not website_id:
            skipped += 1
            continue

        if not store_code or store_code.lower() == "x":
            store_id = None
        else:
            store_id = stores.get((website_id, store_code))
            if not store_id:
                skipped += 1
                continue

        cursor.execute(
            """
                        SELECT pv.id
                        FROM product_variants pv
                        JOIN products p ON pv.product_id = p.id
            JOIN brands b   ON p.brand_id = b.id
            JOIN categories c ON p.category_id = c.id
            JOIN ranges r ON p.range_id = r.id
                        JOIN formats f ON pv.format_id = f.id
                        JOIN packagings pk ON pv.packaging_id = pk.id
            WHERE b.brand_name = %s
              AND c.category_name = %s
              AND r.range_name = %s
              AND f.format_name = %s
              AND pk.packaging_name = %s
            """,
            (brand, category, range_name, fmt, packaging),
        )
        product_variant_row = cursor.fetchone()
        if not product_variant_row:
            skipped += 1
            continue

        product_variant_id = product_variant_row[0]

        cursor.execute(
            """
            SELECT id, currency, data_status FROM weekly_price_summary
                        WHERE product_variant_id = %s
              AND website_id = %s
              AND store_id IS NOT DISTINCT FROM %s
              AND week_start = %s::date
            """,
                        (product_variant_id, website_id, store_id, week_start),
        )
        existing_row = cursor.fetchone()
        if existing_row:
            existing_id, existing_currency, existing_status = existing_row
            should_update_currency = (existing_currency or "").upper() != currency
            should_promote_to_ok = data_status == "OK" and existing_status != "OK"

            if should_promote_to_ok:
                cursor.execute(
                    """
                    UPDATE weekly_price_summary
                    SET avg_price = %s,
                        sample_count = %s,
                        currency = %s,
                        data_status = 'OK',
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (
                        avg_price,
                        sample_count,
                        currency,
                        existing_id,
                    ),
                )
                updated += 1
            elif should_update_currency:
                cursor.execute(
                    "UPDATE weekly_price_summary SET currency = %s, updated_at = NOW() WHERE id = %s",
                    (currency, existing_id),
                )
                updated += 1

            skipped += 1
            continue

        cursor.execute(
            """
            INSERT INTO weekly_price_summary
            (
                product_variant_id,
                website_id,
                store_id,
                week_start,
                avg_price,
                sample_count,
                currency,
                data_status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                product_variant_id,
                website_id,
                store_id,
                week_start,
                avg_price,
                sample_count,
                currency,
                data_status,
            ),
        )
        inserted += 1

    generated_missing = _fill_missing_weeks_to_today(cursor)

    print(f"  ✓ Inserted weekly summary rows: {inserted}")
    print(f"  ✓ Updated weekly summary rows: {updated}")
    print(f"  ✓ Generated missing week rows: {generated_missing}")
    print(f"  ℹ️ Skipped rows: {skipped}")


# =============================================================================
# MAIN
# =============================================================================

def initialize_database():
    print("=" * 50)
    print("CHO Marketwatch System - Database Setup")
    print("=" * 50)

    try:
        rows = load_csv_rows()
        fx_rows = load_historical_fx_rows()
        if not rows:
            print("✗ No data found in CSV.")
            return False

        with get_connection() as conn:
            print("✓ Connected to PostgreSQL")
            with conn.cursor() as cursor:
                insert_websites(cursor, rows)
                insert_brands(cursor, rows)
                insert_categories(cursor, rows)
                insert_ranges(cursor, rows)
                insert_products(cursor, rows)
                insert_formats(cursor, rows)
                insert_packagings(cursor, rows)
                insert_product_variants(cursor, rows)
                insert_stores(cursor, rows)
                insert_product_urls(cursor, rows)
                insert_exchange_rates(cursor, fx_rows)
                insert_weekly_price_summary(cursor, rows)
            conn.commit()

        print("\n" + "=" * 50)
        print("✓ Setup complete!")
        print("=" * 50)
        return True

    except Exception as e:
        print(f"✗ Setup failed: {e}")
        return False


if __name__ == "__main__":
    initialize_database()