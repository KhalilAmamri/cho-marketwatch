import bcrypt

from database.database_config import get_connection


def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed.encode())


def _friendly_db_error_message(exc: Exception) -> str:
    # Keep login errors user-friendly when DB is missing/unreachable/misconfigured.
    if isinstance(exc, UnicodeDecodeError):
        return "Database is unavailable. It may not exist yet or connection settings are invalid. Please verify database configuration and initialize the database."

    message = str(exc).lower()

    if "database" in message and "does not exist" in message:
        return "Database does not exist. Please create it and run database initialization."

    if (
        "could not connect" in message
        or "connection refused" in message
        or "timeout" in message
        or "server closed" in message
    ):
        return "Database server is unavailable. Please start PostgreSQL and verify connection settings."

    return "Database connection failed. Please verify PostgreSQL and database configuration."


def _safe_db_call(func, *args):
    try:
        return func(*args), None
    except Exception as exc:
        return None, _friendly_db_error_message(exc)


def get_user(username: str):
    query = """
        SELECT id, username, password_hash, full_name, role, is_active
        FROM users
        WHERE username = %s
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (username,))
            return cur.fetchone()


def get_user_safe(username: str):
    return _safe_db_call(get_user, username)


def update_last_login(user_id: int):
    query = "UPDATE users SET last_login = NOW() WHERE id = %s"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (user_id,))
        conn.commit()


def update_last_login_safe(user_id: int):
    _, error = _safe_db_call(update_last_login, user_id)
    return error
