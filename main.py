import sys
from etl.run_etl import run_etl
from etl.exchange_rates_etl import fetch_and_store_exchange_rates
from scrapers.scraper_manager import run_all_scrapers

if __name__ == "__main__":
    print("=" * 60)
    print("🔄 CHO Marketwatch System - Starting...")
    print("=" * 60)

    print("\n🔄 Fetching latest FX rates...")
    fetch_and_store_exchange_rates()

    print("\n🔄 Starting Scraping...")
    run_all_scrapers()

    print("\n🔄 Starting ETL Processing...")
    run_etl()

    print("\n" + "=" * 60)
    print("✅ All tasks completed!")
    print("=" * 60)