"""
Admin CRUD operations for CHO MarketWatch
All database write operations used by the Admin Panel
"""
import psycopg2

from database.database_config import get_connection


def _normalize_format(value):
    return str(value or "").strip().replace(" ", "").upper()


def _normalize_packaging(value):
    return str(value or "").strip()


def _fetch_all(query: str, params=None):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            return cur.fetchall()


def _insert_returning_id(query: str, params):
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                result = cur.fetchone()
            conn.commit()
            return result[0] if result else None
    except Exception:
        return None


# ============================================================
# READ — lookup helpers for dropdowns
# ============================================================

def get_all_brands():
    return _fetch_all("SELECT id, brand_name FROM brands ORDER BY brand_name")


def get_all_categories():
    return _fetch_all("SELECT id, category_name FROM categories ORDER BY category_name")


def get_all_ranges():
    return _fetch_all("SELECT id, range_name FROM ranges ORDER BY range_name")


def get_all_websites():
    return _fetch_all("SELECT id, site_name, country FROM websites ORDER BY site_name")


def get_all_stores():
    return _fetch_all(
        """
        SELECT s.id, s.website_id, w.site_name, s.store_code, s.store_name
        FROM stores s
        JOIN websites w ON s.website_id = w.id
        ORDER BY w.site_name, s.store_code
        """
    )


def get_all_formats():
    return _fetch_all(
        """
        SELECT pf.id, b.brand_name, c.category_name,
               r.range_name, pf.format, pf.packaging
        FROM product_formats pf
        JOIN products p      ON pf.product_id = p.id
        JOIN brands b        ON p.brand_id = b.id
        JOIN categories c    ON p.category_id = c.id
        JOIN ranges r        ON p.range_id = r.id
        ORDER BY b.brand_name, pf.format
        """
    )


def get_all_formats_with_ids():
    return _fetch_all(
        """
        SELECT
            pf.id,
            pf.product_id,
            p.brand_id,
            p.category_id,
            p.range_id,
            pf.format,
            pf.packaging,
            b.brand_name,
            c.category_name,
            r.range_name
        FROM product_formats pf
        JOIN products p         ON pf.product_id = p.id
        JOIN brands b           ON p.brand_id = b.id
        JOIN categories c       ON p.category_id = c.id
        JOIN ranges r           ON p.range_id = r.id
        ORDER BY b.brand_name, c.category_name, r.range_name, pf.format, pf.packaging
        """
    )


def get_all_users():
    return _fetch_all(
        """
        SELECT id, username, full_name, role, is_active, last_login
        FROM users
        ORDER BY created_at DESC
        """
    )


def get_all_product_urls():
    return _fetch_all(
        """
        SELECT
            pu.id,
            pu.website_id,
            pu.store_id,
            pu.product_format_id,
            pu.url,
            pu.is_active,
            w.site_name,
            w.country,
            s.store_code,
            s.store_name,
            b.brand_name,
            c.category_name,
            r.range_name,
            pf.format,
            pf.packaging
        FROM product_urls pu
        JOIN websites w        ON pu.website_id = w.id
        LEFT JOIN stores s     ON pu.store_id = s.id
        JOIN product_formats pf ON pu.product_format_id = pf.id
        JOIN products p        ON pf.product_id = p.id
        JOIN brands b          ON p.brand_id = b.id
        JOIN categories c      ON p.category_id = c.id
        JOIN ranges r          ON p.range_id = r.id
        ORDER BY w.site_name, b.brand_name, c.category_name, r.range_name, pf.format, pf.packaging
        """
    )


# ============================================================
# CREATE — add new records
# ============================================================

def add_brand(brand_name: str):
    return _insert_returning_id(
        "INSERT INTO brands (brand_name) VALUES (%s) ON CONFLICT DO NOTHING RETURNING id",
        (brand_name,),
    )


def add_category(category_name: str):
    return _insert_returning_id(
        "INSERT INTO categories (category_name) VALUES (%s) ON CONFLICT DO NOTHING RETURNING id",
        (category_name,),
    )


def add_range(range_name: str):
    return _insert_returning_id(
        "INSERT INTO ranges (range_name) VALUES (%s) ON CONFLICT DO NOTHING RETURNING id",
        (range_name,),
    )


def add_product_format(brand_id, cat_id, range_id, fmt, packaging):
    """
    Inserts into products (if not exists) then into product_formats.
    Returns product_format id or None if already exists.
    """
    fmt = _normalize_format(fmt)
    packaging = _normalize_packaging(packaging)
    if not fmt or not packaging:
        return None

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # Upsert product
                cur.execute("""
                    INSERT INTO products (brand_id, category_id, range_id)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (brand_id, category_id, range_id)
                    DO UPDATE SET brand_id = EXCLUDED.brand_id
                    RETURNING id
                """, (brand_id, cat_id, range_id))
                product_id = cur.fetchone()[0]

                # Insert format
                cur.execute("""
                    INSERT INTO product_formats (product_id, format, packaging)
                    VALUES (%s, %s, %s)
                    ON CONFLICT DO NOTHING
                    RETURNING id
                """, (product_id, fmt, packaging))
                result = cur.fetchone()
            conn.commit()
            return result[0] if result else None
    except Exception:
        return None


def add_product_url(website_id, store_id, product_format_id, url):
    return _insert_returning_id(
        """
        INSERT INTO product_urls (website_id, store_id, product_format_id, url)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT DO NOTHING
        RETURNING id
        """,
        (website_id, store_id, product_format_id, url),
    )


def add_user(username: str, password_hash: str, full_name: str, role: str):
    return _insert_returning_id(
        """
        INSERT INTO users (username, password_hash, full_name, role)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT DO NOTHING
        RETURNING id
        """,
        (username, password_hash, full_name or None, role),
    )


def _cleanup_orphan_products(cur):
    cur.execute(
        """
        DELETE FROM products p
        WHERE NOT EXISTS (
            SELECT 1 FROM product_formats pf WHERE pf.product_id = p.id
        )
        """
    )


def update_product_format(format_id, brand_id, cat_id, range_id, fmt, packaging):
    fmt = _normalize_format(fmt)
    packaging = _normalize_packaging(packaging)
    if not fmt or not packaging:
        return False, "Format and packaging are required."

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM product_formats WHERE id = %s", (format_id,))
                if not cur.fetchone():
                    return False, "Product format not found."

                cur.execute(
                    """
                    INSERT INTO products (brand_id, category_id, range_id)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (brand_id, category_id, range_id)
                    DO UPDATE SET brand_id = EXCLUDED.brand_id
                    RETURNING id
                    """,
                    (brand_id, cat_id, range_id),
                )
                product_id = cur.fetchone()[0]

                cur.execute(
                    """
                    UPDATE product_formats
                    SET product_id = %s, format = %s, packaging = %s
                    WHERE id = %s
                    """,
                    (product_id, fmt, packaging, format_id),
                )

                _cleanup_orphan_products(cur)
            conn.commit()
            return True, "Product updated successfully."
    except psycopg2.errors.UniqueViolation:
        return False, "A product format with these values already exists."
    except Exception as exc:
        return False, f"Update failed: {exc}"


def delete_product_format(format_id: int):
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM scraped_prices WHERE product_format_id = %s", (format_id,))
                observation_count = cur.fetchone()[0]
                if observation_count > 0:
                    return False, "Cannot delete: scraped prices exist for this product format."

                cur.execute("SELECT COUNT(*) FROM weekly_price_summary WHERE product_format_id = %s", (format_id,))
                weekly_count = cur.fetchone()[0]
                if weekly_count > 0:
                    return False, "Cannot delete: weekly summary exists for this product format."

                cur.execute("SELECT COUNT(*) FROM product_urls WHERE product_format_id = %s", (format_id,))
                url_count = cur.fetchone()[0]
                if url_count > 0:
                    return False, "Cannot delete: URLs are still linked to this product format."

                cur.execute("DELETE FROM product_formats WHERE id = %s", (format_id,))
                if cur.rowcount == 0:
                    return False, "Product format not found."

                _cleanup_orphan_products(cur)
            conn.commit()
            return True, "Product deleted successfully."
    except Exception as exc:
        return False, f"Delete failed: {exc}"


# ============================================================
# UPDATE — toggle active status
# ============================================================

def toggle_url_active(url_id: int, is_active: bool):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE product_urls SET is_active = %s WHERE id = %s",
                (is_active, url_id)
            )
        conn.commit()


def toggle_user_active(user_id: int, is_active: bool):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET is_active = %s WHERE id = %s",
                (is_active, user_id)
            )
        conn.commit()


def _count_active_admins(cur):
    cur.execute("SELECT COUNT(*) FROM users WHERE role = 'admin' AND is_active = TRUE")
    return cur.fetchone()[0]


def update_user(user_id: int, full_name: str, role: str, is_active: bool):
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT role, is_active FROM users WHERE id = %s", (user_id,))
                row = cur.fetchone()
                if not row:
                    return False, "User not found."

                current_role, current_active = row
                active_admins_before = _count_active_admins(cur)
                was_active_admin = current_role == "admin" and current_active
                will_be_active_admin = role == "admin" and is_active
                active_admins_after = active_admins_before - (1 if was_active_admin else 0) + (1 if will_be_active_admin else 0)

                if active_admins_after < 1:
                    return False, "At least one active admin account is required."

                cur.execute(
                    """
                    UPDATE users
                    SET full_name = %s,
                        role = %s,
                        is_active = %s
                    WHERE id = %s
                    """,
                    (full_name or None, role, is_active, user_id),
                )
            conn.commit()
            return True, "User updated successfully."
    except Exception as exc:
        return False, f"User update failed: {exc}"


def update_user_password(user_id: int, password_hash: str):
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE users SET password_hash = %s WHERE id = %s",
                    (password_hash, user_id),
                )
                if cur.rowcount == 0:
                    return False, "User not found."
            conn.commit()
            return True, "Password updated successfully."
    except Exception as exc:
        return False, f"Password update failed: {exc}"


# ============================================================
# DELETE
# ============================================================

def delete_product_url(url_id: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM product_urls WHERE id = %s", (url_id,))
        conn.commit()


def delete_user(user_id: int, current_user_id: int | None = None):
    if current_user_id is not None and user_id == current_user_id:
        return False, "You cannot delete your own account."

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT role, is_active FROM users WHERE id = %s", (user_id,))
                row = cur.fetchone()
                if not row:
                    return False, "User not found."

                role, is_active = row
                if role == "admin" and is_active:
                    active_admins = _count_active_admins(cur)
                    if active_admins <= 1:
                        return False, "Cannot delete the last active admin account."

                cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
                if cur.rowcount == 0:
                    return False, "User not found."
            conn.commit()
            return True, "User deleted successfully."
    except Exception as exc:
        return False, f"Delete failed: {exc}"
