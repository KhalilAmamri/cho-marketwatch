import sys
import os
sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))

import requests
from database.database_config import get_connection

REQUIRED_QUOTES = ["SEK"]


def fetch_and_store_exchange_rates():
    params = {
        "from": "EUR",
        "to": ",".join(REQUIRED_QUOTES),
    }
    response = requests.get("https://api.frankfurter.dev/v1/latest", params=params, timeout=10)
    if response.status_code != 200:
        raise Exception(f"HTTP Error: {response.status_code}")

    data = response.json()
    if "rates" not in data:
        raise Exception(f"No rates in response: {data}")

    rates = {k.upper(): v for k, v in data["rates"].items()}
    missing_quotes = [c for c in REQUIRED_QUOTES if c not in rates]
    if missing_quotes:
        raise Exception(f"Missing requested FX rates for: {', '.join(missing_quotes)}")

    fx_date = data["date"]
    rates["EUR"] = 1.0  # Add EUR to the rates for completeness

    with get_connection() as conn:
        with conn.cursor() as cursor:
            for currency in ["EUR", *REQUIRED_QUOTES]:
                rate = rates[currency]
                cursor.execute("""
                    INSERT INTO exchange_rates (currency, date, rate_to_eur)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (currency, date) DO UPDATE SET rate_to_eur = EXCLUDED.rate_to_eur
                """, (currency, fx_date, rate))
            conn.commit()
    print(f"✅ Exchange rates stored for {fx_date}")

if __name__ == "__main__":
    fetch_and_store_exchange_rates()
