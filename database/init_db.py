# database/init_db.py
"""
Database initialization and seeding.
Loads all data from tracking_list/products.csv into the database.

Table order:
    websites → brands → product_types → categories → ranges → products → product_formats → stores → product_urls
"""

import csv
import os
import psycopg2
from urllib.parse import urlparse

from database.database_config import DATABASE_CONFIG


# =============================================================================
# CONFIGURATION
# =============================================================================

CSV_TARGETS_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "tracking_list", "products.csv")
)


# =============================================================================
# CONNECTION
# =============================================================================

def get_connection():
    return psycopg2.connect(
        host=DATABASE_CONFIG["host"],
        port=DATABASE_CONFIG["port"],
        database=DATABASE_CONFIG["database"],
        user=DATABASE_CONFIG["user"],
        password=DATABASE_CONFIG["password"],
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

def insert_product_types(cursor, rows):
    print("\n📌 Inserting product types...")
    seen = set()
    for row in rows:
        product_type = row.get("Product Type", "").strip()
        if not product_type or product_type in seen:
            continue
        seen.add(product_type)
        cursor.execute("SELECT id FROM product_types WHERE product_type = %s", (product_type,))
        if cursor.fetchone():
            print(f"  ✓ {product_type} already exists")
        else:
            cursor.execute("INSERT INTO product_types (product_type) VALUES (%s)", (product_type,))
            print(f"  ✓ Inserted product type: {product_type}")


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
        product_type = row.get("Product Type", "").strip()
        category     = row.get("Category", "").strip()
        range_name   = row.get("Range", "").strip()

        if not brand or not product_type:
            continue

        key = (brand, product_type, category, range_name)
        if key in seen:
            continue
        seen.add(key)

        cursor.execute("SELECT id FROM brands WHERE brand_name = %s", (brand,))
        brand_row = cursor.fetchone()
        if not brand_row:
            print(f"  ⚠️ Brand not found: {brand}")
            continue

        cursor.execute("SELECT id FROM product_types WHERE product_type = %s", (product_type,))
        type_row = cursor.fetchone()
        if not type_row:
            print(f"  ⚠️ Product type not found: {product_type}")
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
        product_type_id = type_row[0]
        category_id     = cat_row[0]
        range_id        = range_row[0]

        cursor.execute(
            "SELECT id FROM products WHERE brand_id = %s AND product_type_id = %s AND category_id = %s AND range_id = %s",
            (brand_id, product_type_id, category_id, range_id)
        )
        if cursor.fetchone():
            print(f"  ✓ {brand} {product_type} {category} {range_name} already exists")
        else:
            cursor.execute(
                "INSERT INTO products (brand_id, product_type_id, category_id, range_id) VALUES (%s, %s, %s, %s)",
                (brand_id, product_type_id, category_id, range_id)
            )
            print(f"  ✓ Inserted product: {brand} {product_type} {category} {range_name}")

def insert_product_formats(cursor, rows):
    print("\n📌 Inserting product formats...")
    seen = set()
    for row in rows:
        brand        = row.get("Brand", "").strip()
        product_type = row.get("Product Type", "").strip()
        category     = row.get("Category", "").strip()
        range_name   = row.get("Range", "").strip()
        fmt          = row.get("Size", "").strip().replace(" ", "").upper()
        packaging    = row.get("Packaging", "").strip()

        if not brand or not product_type or not fmt or not packaging:
            continue

        key = (brand, product_type, category, range_name, fmt, packaging)
        if key in seen:
            continue
        seen.add(key)

        # Get product_id
        cursor.execute(
            """
            SELECT p.id FROM products p
            JOIN brands b    ON p.brand_id        = b.id
            JOIN product_types pt ON p.product_type_id = pt.id
            JOIN categories c  ON p.category_id     = c.id
            JOIN ranges r  ON p.range_id = r.id
            WHERE b.brand_name = %s
              AND pt.product_type = %s
              AND c.category_name = %s
              AND r.range_name = %s
            """,
            (brand, product_type, category, range_name)
        )
        product_row = cursor.fetchone()
        if not product_row:
            print(f"  ⚠️ Product not found: {brand} {product_type} {category} {range_name}")
            continue
        product_id = product_row[0]

        cursor.execute(
            "SELECT id FROM product_formats WHERE product_id = %s AND format = %s AND packaging = %s",
            (product_id, fmt, packaging)
        )
        if cursor.fetchone():
            print(f"  ✓ Variant {fmt} {packaging} already exists for {brand} {product_type} {range_name}")
        else:
            cursor.execute(
                "INSERT INTO product_formats (product_id, format, packaging) VALUES (%s, %s, %s)",
                (product_id, fmt, packaging)
            )
            print(f"  ✓ Inserted format: {brand} {product_type} {category} {range_name} {fmt} {packaging}")


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
        product_type = row.get("Product Type", "").strip()
        category     = row.get("Category", "").strip()
        range_name   = row.get("Range", "").strip()
        fmt          = row.get("Size", "").strip().replace(" ", "").upper()
        packaging    = row.get("Packaging", "").strip()
        store_code   = row.get("Store Code", "").strip()

        if not site_name or not url or not brand or not product_type:
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
            JOIN product_types pt   ON p.product_type_id = pt.id
            JOIN categories c       ON p.category_id     = c.id
            JOIN ranges r           ON p.range_id        = r.id
            WHERE b.brand_name = %s
              AND pt.product_type = %s
              AND c.category_name = %s
              AND r.range_name = %s
              AND pf.format = %s
              AND pf.packaging = %s
            """,
            (brand, product_type, category, range_name, fmt, packaging)
        )
        format_row = cursor.fetchone()
        if not format_row:
            print(f"  ⚠️ Variant not found: {brand} {product_type} {category} {range_name} {fmt} {packaging}")
            continue
        product_format_id = format_row[0]

        # Check duplicate
        cursor.execute(
            "SELECT id FROM product_urls WHERE website_id = %s AND product_format_id = %s AND store_id IS NOT DISTINCT FROM %s",
            (website_id, product_format_id, store_id)
        )
        if cursor.fetchone():
            print(f"  ✓ URL already exists for {site_name}{store_label} - {brand} {product_type} {category} {range_name} {fmt} {packaging}")
            continue

        cursor.execute(
            "INSERT INTO product_urls (website_id, store_id, product_format_id, url) VALUES (%s, %s, %s, %s)",
            (website_id, store_id, product_format_id, url)
        )
        print(f"  ✓ URL inserted for {site_name}{store_label} - {brand} {product_type} {category} {range_name} {fmt} {packaging}")


# =============================================================================
# MAIN
# =============================================================================

def initialize_database():
    print("=" * 50)
    print("CHO Marketwatch System - Database Setup")
    print("=" * 50)

    try:
        rows = load_csv_rows()
        if not rows:
            print("✗ No data found in CSV.")
            return False

        with get_connection() as conn:
            print("✓ Connected to PostgreSQL")
            with conn.cursor() as cursor:
                insert_websites(cursor, rows)
                insert_brands(cursor, rows)
                insert_product_types(cursor, rows)
                insert_categories(cursor, rows)
                insert_ranges(cursor, rows)
                insert_products(cursor, rows)
                insert_product_formats(cursor, rows)
                insert_stores(cursor, rows)
                insert_product_urls(cursor, rows)
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