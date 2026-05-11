from urllib.parse import urlparse

import bcrypt
import psycopg2
from psycopg2 import errorcodes
from psycopg2.extras import RealDictCursor

from app.db.connection import get_connection

PRODUCT_LABEL_SQL = (
    "b.brand_name || ' ' || c.category_name || ' ' || r.range_name || ' ' || f.format_name || ' ' || pk.packaging_name"
)


def _raise_db_validation(exc: psycopg2.Error, duplicate_message: str, foreign_key_message: str):
    if exc.pgcode == errorcodes.UNIQUE_VIOLATION:
        raise ValueError(duplicate_message) from exc
    if exc.pgcode == errorcodes.FOREIGN_KEY_VIOLATION:
        raise ValueError(foreign_key_message) from exc
    raise


def _ensure_product_exists(cur, brand_id: int, category_id: int, range_id: int) -> int:
    cur.execute(
        """
        INSERT INTO products (brand_id, category_id, range_id)
        VALUES (%s, %s, %s)
        ON CONFLICT (brand_id, category_id, range_id)
        DO UPDATE SET brand_id = EXCLUDED.brand_id
        RETURNING id
        """,
        (brand_id, category_id, range_id),
    )
    row = cur.fetchone()
    return int(row["id"])


def _get_product_format_row(cur, product_format_id: int) -> dict:
    cur.execute(
        """
        SELECT
            pv.id,
            p.id AS product_id,
            b.id AS brand_id,
            b.brand_name,
            c.id AS category_id,
            c.category_name,
            r.id AS range_id,
            r.range_name,
            f.format_name AS format,
            pk.packaging_name AS packaging,
            f.volume_value,
            f.volume_unit,
            pv.created_at
        FROM product_variants pv
        JOIN products p ON pv.product_id = p.id
        JOIN formats f ON pv.format_id = f.id
        JOIN packagings pk ON pv.packaging_id = pk.id
        JOIN brands b ON p.brand_id = b.id
        JOIN categories c ON p.category_id = c.id
        JOIN ranges r ON p.range_id = r.id
        WHERE pv.id = %s
        """,
        (product_format_id,),
    )
    row = cur.fetchone()
    if not row:
        raise LookupError("Product format not found")
    return row


def _get_product_url_row(cur, product_url_id: int) -> dict:
    cur.execute(
        f"""
        SELECT
            pu.id,
            pu.website_id,
            w.site_name AS website_name,
            w.country,
            pu.store_id,
            s.store_code,
            pu.product_variant_id AS product_format_id,
            {PRODUCT_LABEL_SQL} AS product_label,
            pu.url,
            pu.is_active,
            pu.created_at
        FROM product_urls pu
        JOIN websites w ON pu.website_id = w.id
        LEFT JOIN stores s ON pu.store_id = s.id
        JOIN product_variants pv ON pu.product_variant_id = pv.id
        JOIN products p ON pv.product_id = p.id
        JOIN formats f ON pv.format_id = f.id
        JOIN packagings pk ON pv.packaging_id = pk.id
        JOIN brands b ON p.brand_id = b.id
        JOIN categories c ON p.category_id = c.id
        JOIN ranges r ON p.range_id = r.id
        WHERE pu.id = %s
        """,
        (product_url_id,),
    )
    row = cur.fetchone()
    if not row:
        raise LookupError("Product URL not found")
    return row


def _get_website_row(cur, website_id: int) -> dict:
    cur.execute(
        """
        SELECT id, site_name, base_url, country, scraper_status, created_at
        FROM websites
        WHERE id = %s
        """,
        (website_id,),
    )
    row = cur.fetchone()
    if not row:
        raise LookupError("Website not found")
    return row


def _ensure_website_is_active(cur, website_id: int) -> None:
    cur.execute(
        """
        SELECT scraper_status
        FROM websites
        WHERE id = %s
        """,
        (website_id,),
    )
    row = cur.fetchone()
    if not row:
        raise ValueError("Invalid website")
    if row["scraper_status"] != "active":
        raise ValueError("Website must be active before linking product URLs")


def _normalize_website_payload(payload: dict) -> tuple[str, str, str]:
    site_name = str(payload["site_name"]).strip()
    if not site_name:
        raise ValueError("Website name cannot be empty")

    raw_base_url = payload.get("base_url")
    base_url = raw_base_url.strip() if isinstance(raw_base_url, str) else ""
    if not base_url:
        raise ValueError("Website base_url is required")

    parsed = urlparse(base_url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("Website base_url must be a valid HTTP or HTTPS URL")

    raw_country = payload.get("country")
    country = raw_country.strip() if isinstance(raw_country, str) else ""
    if not country:
        raise ValueError("Website country is required")

    return site_name, base_url, country


def _get_store_row(cur, store_id: int) -> dict:
    cur.execute(
        """
        SELECT
            s.id,
            s.website_id,
            w.site_name AS website_name,
            w.country,
            s.store_code,
            s.store_name,
            CASE
                WHEN s.store_name IS NULL OR s.store_name = ''
                    THEN w.site_name || ' (' || s.store_code || ')'
                ELSE w.site_name || ' (' || s.store_code || ' - ' || s.store_name || ')'
            END AS label,
            s.created_at
        FROM stores s
        JOIN websites w ON s.website_id = w.id
        WHERE s.id = %s
        """,
        (store_id,),
    )
    row = cur.fetchone()
    if not row:
        raise LookupError("Store not found")
    return row


def _normalize_store_payload(payload: dict) -> tuple[int, str, str | None]:
    website_id = int(payload["website_id"])
    store_code = str(payload["store_code"]).strip()
    if not store_code:
        raise ValueError("Store code cannot be empty")

    raw_name = payload.get("store_name")
    store_name = raw_name.strip() if isinstance(raw_name, str) else None
    if store_name == "":
        store_name = None

    return website_id, store_code, store_name


def _get_user_row(cur, user_id: int) -> dict:
    cur.execute(
        """
        SELECT id, username, full_name, role, is_active, created_at, last_login
        FROM users
        WHERE id = %s
        """,
        (user_id,),
    )
    row = cur.fetchone()
    if not row:
        raise LookupError("User not found")
    return row


def _ensure_remaining_active_admin(cur):
    cur.execute("SELECT COUNT(*) AS total FROM users WHERE role = 'admin' AND is_active = TRUE")
    row = cur.fetchone()
    if int(row["total"]) <= 1:
        raise ValueError("At least one active admin user must remain")


def _create_named_lookup(table: str, column: str, value: str) -> dict:
    normalized = value.strip()
    if not normalized:
        raise ValueError("Name cannot be empty")

    with get_connection() as conn:
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    f"""
                    INSERT INTO {table} ({column})
                    VALUES (%s)
                    RETURNING id, {column} AS name
                    """,
                    (normalized,),
                )
                row = cur.fetchone()
            conn.commit()
            return row
        except psycopg2.Error as exc:
            conn.rollback()
            if exc.pgcode == errorcodes.UNIQUE_VIOLATION:
                raise ValueError(f"{normalized} already exists") from exc
            raise


def create_brand(name: str) -> dict:
    return _create_named_lookup("brands", "brand_name", name)


def create_category(name: str) -> dict:
    return _create_named_lookup("categories", "category_name", name)


def create_range(name: str) -> dict:
    return _create_named_lookup("ranges", "range_name", name)


def create_format(payload: dict) -> dict:
    name = str(payload["name"]).strip()
    volume_value = float(payload["volume_value"])
    volume_unit = str(payload["volume_unit"]).strip().upper()
    if not name:
        raise ValueError("Format name cannot be empty")

    with get_connection() as conn:
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO formats (format_name, volume_value, volume_unit)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (format_name)
                    DO UPDATE SET volume_value = EXCLUDED.volume_value,
                                  volume_unit = EXCLUDED.volume_unit
                    RETURNING id, format_name AS name
                    """,
                    (name, volume_value, volume_unit),
                )
                row = cur.fetchone()
            conn.commit()
            return row
        except psycopg2.Error as exc:
            conn.rollback()
            _raise_db_validation(exc, f"{name} already exists", "Invalid format payload")


def create_packaging(name: str) -> dict:
    return _create_named_lookup("packagings", "packaging_name", name)


def get_admin_lookups() -> dict:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, brand_name AS name FROM brands ORDER BY brand_name")
            brands = cur.fetchall()

            cur.execute("SELECT id, category_name AS name FROM categories ORDER BY category_name")
            categories = cur.fetchall()

            cur.execute("SELECT id, range_name AS name FROM ranges ORDER BY range_name")
            ranges = cur.fetchall()

            cur.execute("SELECT id, site_name, base_url, country, scraper_status FROM websites ORDER BY site_name")
            websites = cur.fetchall()

            cur.execute(
                """
                SELECT
                    s.id,
                    s.website_id,
                    w.site_name AS website_name,
                    s.store_code,
                    s.store_name,
                    CASE
                        WHEN s.store_name IS NULL OR s.store_name = ''
                            THEN w.site_name || ' (' || s.store_code || ')'
                        ELSE w.site_name || ' (' || s.store_code || ' - ' || s.store_name || ')'
                    END AS label
                FROM stores s
                JOIN websites w ON s.website_id = w.id
                ORDER BY w.site_name, s.store_code
                """
            )
            stores = cur.fetchall()

            cur.execute(
                f"""
                SELECT
                    pv.id,
                    {PRODUCT_LABEL_SQL} AS label
                FROM product_variants pv
                JOIN products p ON pv.product_id = p.id
                JOIN formats f ON pv.format_id = f.id
                JOIN packagings pk ON pv.packaging_id = pk.id
                JOIN brands b ON p.brand_id = b.id
                JOIN categories c ON p.category_id = c.id
                JOIN ranges r ON p.range_id = r.id
                ORDER BY label
                """
            )
            product_formats = cur.fetchall()

            cur.execute(
                """
                SELECT format_name AS format
                FROM formats
                WHERE format_name IS NOT NULL AND BTRIM(format_name) <> ''
                ORDER BY format_name
                """
            )
            formats = [row["format"] for row in cur.fetchall()]

            cur.execute(
                """
                SELECT packaging_name AS packaging
                FROM packagings
                WHERE packaging_name IS NOT NULL AND BTRIM(packaging_name) <> ''
                ORDER BY packaging_name
                """
            )
            packagings = [row["packaging"] for row in cur.fetchall()]

    return {
        "brands": brands,
        "categories": categories,
        "ranges": ranges,
        "websites": websites,
        "stores": stores,
        "product_formats": product_formats,
        "formats": formats,
        "packagings": packagings,
    }


def list_websites() -> list[dict]:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, site_name, base_url, country, scraper_status, created_at
                FROM websites
                ORDER BY site_name
                """
            )
            return cur.fetchall()


def create_website(payload: dict) -> dict:
    site_name, base_url, country = _normalize_website_payload(payload)

    with get_connection() as conn:
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO websites (site_name, base_url, country, scraper_status)
                    VALUES (%s, %s, %s, 'pending')
                    RETURNING id
                    """,
                    (site_name, base_url, country),
                )
                created = cur.fetchone()
                row = _get_website_row(cur, int(created["id"]))
            conn.commit()
            return row
        except psycopg2.Error as exc:
            conn.rollback()
            _raise_db_validation(exc, "Website name already exists", "Invalid website payload")


def update_website(website_id: int, payload: dict) -> dict:
    site_name, base_url, country = _normalize_website_payload(payload)

    with get_connection() as conn:
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    UPDATE websites
                    SET site_name = %s,
                        base_url = %s,
                        country = %s
                    WHERE id = %s
                    RETURNING id
                    """,
                    (site_name, base_url, country, website_id),
                )
                updated = cur.fetchone()
                if not updated:
                    raise LookupError("Website not found")
                row = _get_website_row(cur, website_id)
            conn.commit()
            return row
        except psycopg2.Error as exc:
            conn.rollback()
            _raise_db_validation(exc, "Website name already exists", "Invalid website payload")


def delete_website(website_id: int) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM websites WHERE id = %s RETURNING id", (website_id,))
            deleted = cur.fetchone()
            if not deleted:
                raise LookupError("Website not found")
        conn.commit()


def list_stores() -> list[dict]:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    s.id,
                    s.website_id,
                    w.site_name AS website_name,
                    w.country,
                    s.store_code,
                    s.store_name,
                    CASE
                        WHEN s.store_name IS NULL OR s.store_name = ''
                            THEN w.site_name || ' (' || s.store_code || ')'
                        ELSE w.site_name || ' (' || s.store_code || ' - ' || s.store_name || ')'
                    END AS label,
                    s.created_at
                FROM stores s
                JOIN websites w ON s.website_id = w.id
                ORDER BY w.site_name, s.store_code
                """
            )
            return cur.fetchall()


def create_store(payload: dict) -> dict:
    website_id, store_code, store_name = _normalize_store_payload(payload)

    with get_connection() as conn:
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO stores (website_id, store_code, store_name)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                    (website_id, store_code, store_name),
                )
                created = cur.fetchone()
                row = _get_store_row(cur, int(created["id"]))
            conn.commit()
            return row
        except psycopg2.Error as exc:
            conn.rollback()
            _raise_db_validation(exc, "Store code already exists for this website", "Invalid website")


def update_store(store_id: int, payload: dict) -> dict:
    website_id, store_code, store_name = _normalize_store_payload(payload)

    with get_connection() as conn:
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    UPDATE stores
                    SET website_id = %s,
                        store_code = %s,
                        store_name = %s
                    WHERE id = %s
                    RETURNING id
                    """,
                    (website_id, store_code, store_name, store_id),
                )
                updated = cur.fetchone()
                if not updated:
                    raise LookupError("Store not found")
                row = _get_store_row(cur, store_id)
            conn.commit()
            return row
        except psycopg2.Error as exc:
            conn.rollback()
            _raise_db_validation(exc, "Store code already exists for this website", "Invalid website")


def delete_store(store_id: int) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM stores WHERE id = %s RETURNING id", (store_id,))
            deleted = cur.fetchone()
            if not deleted:
                raise LookupError("Store not found")
        conn.commit()


def list_product_formats() -> list[dict]:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    pv.id,
                    p.id AS product_id,
                    b.id AS brand_id,
                    b.brand_name,
                    c.id AS category_id,
                    c.category_name,
                    r.id AS range_id,
                    r.range_name,
                    f.format_name AS format,
                    pk.packaging_name AS packaging,
                    f.volume_value,
                    f.volume_unit,
                    pv.created_at
                FROM product_variants pv
                JOIN products p ON pv.product_id = p.id
                JOIN formats f ON pv.format_id = f.id
                JOIN packagings pk ON pv.packaging_id = pk.id
                JOIN brands b ON p.brand_id = b.id
                JOIN categories c ON p.category_id = c.id
                JOIN ranges r ON p.range_id = r.id
                ORDER BY b.brand_name, c.category_name, r.range_name, f.format_name, pk.packaging_name
                """
            )
            return cur.fetchall()


def create_product_format(payload: dict) -> dict:
    with get_connection() as conn:
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                product_id = _ensure_product_exists(
                    cur,
                    payload["brand_id"],
                    payload["category_id"],
                    payload["range_id"],
                )
                format_name = str(payload["format"]).strip()
                packaging_name = str(payload["packaging"]).strip()
                volume_value = float(payload["volume_value"])
                volume_unit = str(payload["volume_unit"]).strip().upper()
                if not format_name:
                    raise ValueError("Format cannot be empty")
                if not packaging_name:
                    raise ValueError("Packaging cannot be empty")

                cur.execute("SELECT id FROM formats WHERE format_name = %s", (format_name,))
                format_row = cur.fetchone()
                if not format_row:
                    cur.execute(
                        "INSERT INTO formats (format_name, volume_value, volume_unit) VALUES (%s, %s, %s) RETURNING id",
                        (format_name, volume_value, volume_unit),
                    )
                    format_row = cur.fetchone()
                else:
                    cur.execute(
                        "UPDATE formats SET volume_value = %s, volume_unit = %s WHERE id = %s",
                        (volume_value, volume_unit, int(format_row["id"])),
                    )

                cur.execute("SELECT id FROM packagings WHERE packaging_name = %s", (packaging_name,))
                packaging_row = cur.fetchone()
                if not packaging_row:
                    raise ValueError("Packaging not found in master data")

                cur.execute(
                    """
                    INSERT INTO product_variants (product_id, format_id, packaging_id)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                    (product_id, int(format_row["id"]), int(packaging_row["id"])),
                )
                created = cur.fetchone()
                row = _get_product_format_row(cur, int(created["id"]))
            conn.commit()
            return row
        except psycopg2.Error as exc:
            conn.rollback()
            _raise_db_validation(
                exc,
                "Product format already exists",
                "Invalid brand, category, range, format, or packaging",
            )


def update_product_format(product_format_id: int, payload: dict) -> dict:
    with get_connection() as conn:
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                product_id = _ensure_product_exists(
                    cur,
                    payload["brand_id"],
                    payload["category_id"],
                    payload["range_id"],
                )
                format_name = str(payload["format"]).strip()
                packaging_name = str(payload["packaging"]).strip()
                volume_value = float(payload["volume_value"])
                volume_unit = str(payload["volume_unit"]).strip().upper()
                if not format_name:
                    raise ValueError("Format cannot be empty")
                if not packaging_name:
                    raise ValueError("Packaging cannot be empty")

                cur.execute("SELECT id FROM formats WHERE format_name = %s", (format_name,))
                format_row = cur.fetchone()
                if not format_row:
                    cur.execute(
                        "INSERT INTO formats (format_name, volume_value, volume_unit) VALUES (%s, %s, %s) RETURNING id",
                        (format_name, volume_value, volume_unit),
                    )
                    format_row = cur.fetchone()
                else:
                    cur.execute(
                        "UPDATE formats SET volume_value = %s, volume_unit = %s WHERE id = %s",
                        (volume_value, volume_unit, int(format_row["id"])),
                    )

                cur.execute("SELECT id FROM packagings WHERE packaging_name = %s", (packaging_name,))
                packaging_row = cur.fetchone()
                if not packaging_row:
                    raise ValueError("Packaging not found in master data")

                cur.execute(
                    """
                    UPDATE product_variants
                    SET product_id = %s,
                        format_id = %s,
                        packaging_id = %s
                    WHERE id = %s
                    RETURNING id
                    """,
                    (
                        product_id,
                        int(format_row["id"]),
                        int(packaging_row["id"]),
                        product_format_id,
                    ),
                )
                updated = cur.fetchone()
                if not updated:
                    raise LookupError("Product format not found")
                row = _get_product_format_row(cur, product_format_id)
            conn.commit()
            return row
        except psycopg2.Error as exc:
            conn.rollback()
            _raise_db_validation(
                exc,
                "Product format already exists",
                "Invalid brand, category, range, format, or packaging",
            )


def delete_product_format(product_format_id: int) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM product_variants WHERE id = %s RETURNING id", (product_format_id,))
            deleted = cur.fetchone()
            if not deleted:
                raise LookupError("Product format not found")
        conn.commit()


def list_product_urls() -> list[dict]:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                f"""
                SELECT
                    pu.id,
                    pu.website_id,
                    w.site_name AS website_name,
                    w.country,
                    pu.store_id,
                    s.store_code,
                    pu.product_variant_id AS product_format_id,
                    {PRODUCT_LABEL_SQL} AS product_label,
                    pu.url,
                    pu.is_active,
                    pu.created_at
                FROM product_urls pu
                JOIN websites w ON pu.website_id = w.id
                LEFT JOIN stores s ON pu.store_id = s.id
                JOIN product_variants pv ON pu.product_variant_id = pv.id
                JOIN products p ON pv.product_id = p.id
                JOIN formats f ON pv.format_id = f.id
                JOIN packagings pk ON pv.packaging_id = pk.id
                JOIN brands b ON p.brand_id = b.id
                JOIN categories c ON p.category_id = c.id
                JOIN ranges r ON p.range_id = r.id
                ORDER BY product_label, w.site_name, s.store_code
                """
            )
            return cur.fetchall()


def create_product_url(payload: dict) -> dict:
    with get_connection() as conn:
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                _ensure_website_is_active(cur, int(payload["website_id"]))
                cur.execute(
                    """
                    INSERT INTO product_urls (website_id, store_id, product_variant_id, url, is_active)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        payload["website_id"],
                        payload.get("store_id"),
                        payload["product_format_id"],
                        payload["url"],
                        payload.get("is_active", True),
                    ),
                )
                created = cur.fetchone()
                row = _get_product_url_row(cur, int(created["id"]))
            conn.commit()
            return row
        except psycopg2.Error as exc:
            conn.rollback()
            _raise_db_validation(exc, "Product URL already exists", "Invalid website, store, or product format")


def update_product_url(product_url_id: int, payload: dict) -> dict:
    with get_connection() as conn:
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                _ensure_website_is_active(cur, int(payload["website_id"]))
                cur.execute(
                    """
                    UPDATE product_urls
                    SET website_id = %s,
                        store_id = %s,
                        product_variant_id = %s,
                        url = %s,
                        is_active = %s
                    WHERE id = %s
                    RETURNING id
                    """,
                    (
                        payload["website_id"],
                        payload.get("store_id"),
                        payload["product_format_id"],
                        payload["url"],
                        payload.get("is_active", True),
                        product_url_id,
                    ),
                )
                updated = cur.fetchone()
                if not updated:
                    raise LookupError("Product URL not found")
                row = _get_product_url_row(cur, product_url_id)
            conn.commit()
            return row
        except psycopg2.Error as exc:
            conn.rollback()
            _raise_db_validation(exc, "Product URL already exists", "Invalid website, store, or product format")


def set_product_url_active(product_url_id: int, is_active: bool) -> dict:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                UPDATE product_urls
                SET is_active = %s
                WHERE id = %s
                RETURNING id
                """,
                (is_active, product_url_id),
            )
            updated = cur.fetchone()
            if not updated:
                raise LookupError("Product URL not found")
            row = _get_product_url_row(cur, product_url_id)
        conn.commit()
        return row


def delete_product_url(product_url_id: int) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM product_urls WHERE id = %s RETURNING id", (product_url_id,))
            deleted = cur.fetchone()
            if not deleted:
                raise LookupError("Product URL not found")
        conn.commit()


def list_users() -> list[dict]:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, username, full_name, role, is_active, created_at, last_login
                FROM users
                ORDER BY id
                """
            )
            return cur.fetchall()


def create_user(payload: dict) -> dict:
    password_hash = bcrypt.hashpw(payload["password"].encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    with get_connection() as conn:
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO users (username, password_hash, full_name, role, is_active)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        payload["username"],
                        password_hash,
                        payload.get("full_name"),
                        payload.get("role", "user"),
                        payload.get("is_active", True),
                    ),
                )
                created = cur.fetchone()
                row = _get_user_row(cur, int(created["id"]))
            conn.commit()
            return row
        except psycopg2.Error as exc:
            conn.rollback()
            _raise_db_validation(exc, "Username already exists", "Invalid user payload")


def update_user(user_id: int, updates: dict, current_user_id: int) -> dict:
    with get_connection() as conn:
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, full_name, role, is_active
                    FROM users
                    WHERE id = %s
                    FOR UPDATE
                    """,
                    (user_id,),
                )
                existing = cur.fetchone()
                if not existing:
                    raise LookupError("User not found")

                next_full_name = updates.get("full_name", existing["full_name"])
                next_role = updates.get("role", existing["role"])
                next_is_active = updates.get("is_active", existing["is_active"])

                if user_id == current_user_id:
                    if next_role != "admin":
                        raise PermissionError("You cannot remove your own admin role")
                    if not next_is_active:
                        raise PermissionError("You cannot deactivate your own account")

                if existing["role"] == "admin" and existing["is_active"] and (next_role != "admin" or not next_is_active):
                    _ensure_remaining_active_admin(cur)

                cur.execute(
                    """
                    UPDATE users
                    SET full_name = %s,
                        role = %s,
                        is_active = %s
                    WHERE id = %s
                    RETURNING id
                    """,
                    (next_full_name, next_role, next_is_active, user_id),
                )
                updated = cur.fetchone()
                if not updated:
                    raise LookupError("User not found")
                row = _get_user_row(cur, user_id)
            conn.commit()
            return row
        except psycopg2.Error as exc:
            conn.rollback()
            _raise_db_validation(exc, "Invalid user update", "Invalid user update")


def set_user_active(user_id: int, is_active: bool, current_user_id: int) -> dict:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, role, is_active
                FROM users
                WHERE id = %s
                FOR UPDATE
                """,
                (user_id,),
            )
            existing = cur.fetchone()
            if not existing:
                raise LookupError("User not found")

            if user_id == current_user_id and not is_active:
                raise PermissionError("You cannot deactivate your own account")

            if existing["role"] == "admin" and existing["is_active"] and not is_active:
                _ensure_remaining_active_admin(cur)

            cur.execute(
                """
                UPDATE users
                SET is_active = %s
                WHERE id = %s
                RETURNING id
                """,
                (is_active, user_id),
            )
            updated = cur.fetchone()
            if not updated:
                raise LookupError("User not found")
            row = _get_user_row(cur, user_id)
        conn.commit()
        return row


def delete_user(user_id: int, current_user_id: int) -> None:
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, role, is_active
                FROM users
                WHERE id = %s
                FOR UPDATE
                """,
                (user_id,),
            )
            existing = cur.fetchone()
            if not existing:
                raise LookupError("User not found")

            if user_id == current_user_id:
                raise PermissionError("You cannot delete your own account")

            if existing["role"] == "admin" and existing["is_active"]:
                _ensure_remaining_active_admin(cur)

            cur.execute("DELETE FROM users WHERE id = %s RETURNING id", (user_id,))
            deleted = cur.fetchone()
            if not deleted:
                raise LookupError("User not found")
        conn.commit()
