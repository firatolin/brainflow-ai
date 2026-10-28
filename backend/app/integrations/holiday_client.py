"""Nager.Date client with caching + deterministic demo fallback."""
from __future__ import annotations

import time
from datetime import date

import httpx

from app.core.config import settings


_CACHE_TTL_SECONDS = 6 * 60 * 60  # 6h
_cache: dict[tuple[str, int], tuple[float, list[dict]]] = {}


def _fetch_year(country: str, year: int) -> list[dict]:
    url = f"{settings.NAGER_DATE_BASE_URL}/PublicHolidays/{year}/{country}"
    try:
        with httpx.Client(timeout=settings.EXTERNAL_TIMEOUT_SECONDS) as client:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.json()
            if not isinstance(data, list):
                raise ValueError("unexpected shape")
            return [
                {"date": item.get("date"), "name": item.get("localName") or item.get("name"), "source": "nager"}
                for item in data
            ]
    except Exception:  # noqa: BLE001
        return []


def get_holidays(country: str | None = None, year: int | None = None) -> list[dict]:
    country = (country or settings.PUBLIC_HOLIDAY_COUNTRY).upper()
    year = year or date.today().year
    key = (country, year)
    now = time.time()
    cached = _cache.get(key)
    if cached and now - cached[0] < _CACHE_TTL_SECONDS:
        return cached[1]
    data = _fetch_year(country, year)
    _cache[key] = (now, data)
    return data


def is_holiday(country: str | None, day: date) -> dict | None:
    holidays = get_holidays(country, day.year)
    for h in holidays:
        if h.get("date") == day.isoformat():
            return h
    return None


def clear_cache() -> None:
    _cache.clear()
