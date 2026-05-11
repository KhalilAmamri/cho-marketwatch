from __future__ import annotations

import re
from functools import lru_cache

import pycountry


_OVERRIDES_NAME_TO_ISO3: dict[str, str] = {
    "sweden": "SWE",
    "finland": "FIN",
    "czech republic": "CZE",
    "czechia": "CZE",
    "united kingdom": "GBR",
    "uk": "GBR",
    "russia": "RUS",
    "iran": "IRN",
    "south korea": "KOR",
    "north korea": "PRK",
    "syria": "SYR",
    "vietnam": "VNM",
    "laos": "LAO",
    "bolivia": "BOL",
    "venezuela": "VEN",
    "tanzania": "TZA",
}


def normalize_country_name(name: str | None) -> str:
    value = str(name or "").strip()
    value = re.sub(r"\s+", " ", value)
    return value.casefold()


@lru_cache(maxsize=512)
def country_name_to_iso3(name: str | None) -> str | None:
    key = normalize_country_name(name)
    if not key:
        return None

    override = _OVERRIDES_NAME_TO_ISO3.get(key)
    if override:
        return override

    try:
        country = pycountry.countries.lookup(key)
        alpha_3 = getattr(country, "alpha_3", None)
        return str(alpha_3) if alpha_3 else None
    except LookupError:
        return None
