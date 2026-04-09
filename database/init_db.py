# database/init_db.py
"""
Database initialization and seeding.
Loads all data from the company weekly historical CSV into the database.

Table order:
    websites → brands → categories → ranges → products → product_formats → stores → product_urls
    → exchange_rates → weekly_price_summary
"""

import csv
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

        parsed   = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme else ""
        seen[site_name] = True

        cursor.execute("SELECT id FROM websites WHERE site_name = %s", (site_name,))
        if cursor.fetchone():
            print(f"  ✓ {site_name} already exists")
        else:
            cursor.execute(
                "INSERT INTO websites (site_name, base_url, country) VALUES (%s, %s, %s)",
                (site_name, base_url, country)
            )
            print(f"  ✓ Inserted website: {site_name}")


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

def insert_product_formats(cursor, rows):
    print("\n📌 Inserting product formats...")
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
            JOIN brands b    ON p.brand_id        = b.id
            JOIN categories c  ON p.category_id     = c.id
            JOIN ranges r  ON p.range_id = r.id
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

        cursor.execute(
            "SELECT id FROM product_formats WHERE product_id = %s AND format = %s AND packaging = %s",
            (product_id, fmt, packaging)
        )
        if cursor.fetchone():
            print(f"  ✓ Variant {fmt} {packaging} already exists for {brand} {range_name}")
        else:
            cursor.execute(
                "INSERT INTO product_formats (product_id, format, packaging) VALUES (%s, %s, %s)",
                (product_id, fmt, packaging)
            )
            print(f"  ✓ Inserted format: {brand} {category} {range_name} {fmt} {packaging}")


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

        # Get product_format_id
        cursor.execute(
            """
            SELECT pf.id FROM product_formats pf
            JOIN products p         ON pf.product_id  = p.id
            JOIN brands b           ON p.brand_id     = b.id
            JOIN categories c       ON p.category_id     = c.id
            JOIN ranges r           ON p.range_id        = r.id
            WHERE b.brand_name = %s
              AND c.category_name = %s
              AND r.range_name = %s
              AND pf.format = %s
              AND pf.packaging = %s
            """,
            (brand, category, range_name, fmt, packaging)
        )
        format_row = cursor.fetchone()
        if not format_row:
            print(f"  ⚠️ Variant not found: {brand} {category} {range_name} {fmt} {packaging}")
            continue
        product_format_id = format_row[0]

        # Check duplicate
        cursor.execute(
            "SELECT id FROM product_urls WHERE website_id = %s AND product_format_id = %s AND store_id IS NOT DISTINCT FROM %s",
            (website_id, product_format_id, store_id)
        )
        if cursor.fetchone():
            print(f"  ✓ URL already exists for {site_name}{store_label} - {brand} {category} {range_name} {fmt} {packaging}")
            continue

        cursor.execute(
            "INSERT INTO product_urls (website_id, store_id, product_format_id, url) VALUES (%s, %s, %s, %s)",
            (website_id, store_id, product_format_id, url)
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


def insert_weekly_price_summary(cursor, rows):
    print("\n📌 Inserting weekly price summary...")

    cursor.execute("SELECT id, site_name FROM websites")
    websites = {row[1]: row[0] for row in cursor.fetchall()}

    cursor.execute("SELECT id, website_id, store_code FROM stores")
    stores = {(row[1], row[2]): row[0] for row in cursor.fetchall()}

    inserted = 0
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

        if price is None or price <= 0 or not week_start or not currency:
            skipped += 1
            continue

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
            SELECT pf.id
            FROM product_formats pf
            JOIN products p ON pf.product_id = p.id
            JOIN brands b   ON p.brand_id = b.id
            JOIN categories c ON p.category_id = c.id
            JOIN ranges r ON p.range_id = r.id
            WHERE b.brand_name = %s
              AND c.category_name = %s
              AND r.range_name = %s
              AND pf.format = %s
              AND pf.packaging = %s
            """,
            (brand, category, range_name, fmt, packaging),
        )
        product_format_row = cursor.fetchone()
        if not product_format_row:
            skipped += 1
            continue

        product_format_id = product_format_row[0]

        cursor.execute(
            """
            SELECT id, currency FROM weekly_price_summary
            WHERE product_format_id = %s
              AND website_id = %s
              AND store_id IS NOT DISTINCT FROM %s
              AND week_start = %s::date
            """,
            (product_format_id, website_id, store_id, week_start),
        )
        existing_row = cursor.fetchone()
        if existing_row:
            existing_id, existing_currency = existing_row
            if (existing_currency or "").upper() != currency:
                cursor.execute(
                    "UPDATE weekly_price_summary SET currency = %s WHERE id = %s",
                    (currency, existing_id),
                )
            skipped += 1
            continue

        cursor.execute(
            """
            INSERT INTO weekly_price_summary
            (
                product_format_id,
                website_id,
                store_id,
                week_start,
                avg_price,
                sample_count,
                currency
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                product_format_id,
                website_id,
                store_id,
                week_start,
                price,
                1,
                currency,
            ),
        )
        inserted += 1

    print(f"  ✓ Inserted weekly summary rows: {inserted}")
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
                insert_product_formats(cursor, rows)
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