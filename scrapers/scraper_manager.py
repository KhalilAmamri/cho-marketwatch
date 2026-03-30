from scrapers.sites.coop import scrape_products as scrape_coop
from scrapers.sites.ica import scrape_products as scrape_ica
from scrapers.sites.kesko import scrape_products as scrape_kesko
from scrapers.sites.sok import scrape_products as scrape_sok
from scrapers.sites.citygross import scrape_products as scrape_citygross

def run_all_scrapers():
    scrapers = [
        ("Coop", scrape_coop, "Sweden"),
        ("Ica", scrape_ica, "Sweden"),
        ("Citygross", scrape_citygross, "Sweden"),
        ("Kesko", scrape_kesko, "Finland"),
        ("Sok", scrape_sok, "Finland"),
        # Add any new website scraper here!
    ]
    for idx, (name, func, country) in enumerate(scrapers):
        if idx > 0:
            print()
        print(f"🌍 Country: {country}")
        func(name)
