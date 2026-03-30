import sys
import os
sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))

import requests
import psycopg2
from database.database_config import DATABASE_CONFIG

def get_connection():
    return psycopg2.connect(
        host=DATABASE_CONFIG["host"],
        port=DATABASE_CONFIG["port"],
        database=DATABASE_CONFIG["database"],
        user=DATABASE_CONFIG["user"],
        password=DATABASE_CONFIG["password"],
    )

def fetch_and_store_exchange_rates():
    url = "https://api.frankfurter.dev/v1/latest?from=EUR"
    response = requests.get(url, timeout=10)
    if response.status_code != 200:
        raise Exception(f"HTTP Error: {response.status_code}")
    data = response.json()
    if "rates" not in data:
        raise Exception(f"No rates in response: {data}")
    rates = data["rates"]
    fx_date = data["date"]
    rates["EUR"] = 1.0  # Add EUR to the rates for completeness

    with get_connection() as conn:
        with conn.cursor() as cursor:
            for currency, rate in rates.items():
                cursor.execute("""
                    INSERT INTO exchange_rates (currency, date, rate_to_eur)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (currency, date) DO UPDATE SET rate_to_eur = EXCLUDED.rate_to_eur
                """, (currency, fx_date, rate))
            conn.commit()
    print(f"✅ Exchange rates stored for {fx_date}")

if __name__ == "__main__":
    fetch_and_store_exchange_rates()
