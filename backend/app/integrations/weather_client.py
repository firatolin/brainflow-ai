"""Open-Meteo client with caching + deterministic demo fallback."""
from __future__ import annotations

import time
from dataclasses import dataclass, asdict

import httpx

from app.core.config import settings


# Addis Ababa default coordinates (per-zone overrides can be added later)
ZONE_COORDS: dict[str, tuple[float, float]] = {
    "central": (9.0100, 38.7600),
    "north":   (9.0500, 38.7300),
    "south":   (8.9500, 38.7500),
    "east":    (9.0300, 38.8300),
    "west":    (9.0200, 38.6700),
    "airport": (8.9779, 38.7993),
}

# Demo fallback: deterministic so tests/scenarios are reproducible
DEMO_WEATHER = {
    "central": {"temperature_c": 22.0, "precipitation_mm": 0.0, "wind_kph": 8.0, "severity": 0.1, "conditions": "clear"},
    "north":   {"temperature_c": 21.0, "precipitation_mm": 0.0, "wind_kph": 10.0, "severity": 0.15, "conditions": "clear"},
    "south":   {"temperature_c": 24.0, "precipitation_mm": 0.0, "wind_kph": 6.0, "severity": 0.1, "conditions": "clear"},
    "east":    {"temperature_c": 20.0, "precipitation_mm": 4.5, "wind_kph": 18.0, "severity": 0.55, "conditions": "rain"},
    "west":    {"temperature_c": 23.0, "precipitation_mm": 0.0, "wind_kph": 7.0, "severity": 0.1, "conditions": "clear"},
    "airport": {"temperature_c": 19.0, "precipitation_mm": 2.5, "wind_kph": 22.0, "severity": 0.45, "conditions": "showers"},
}

_CACHE_TTL_SECONDS = 10 * 60
_cache: dict[str, tuple[float, dict]] = {}


@dataclass
class WeatherSnapshot:
    zone: str
    temperature_c: float
    precipitation_mm: float
    wind_kph: float
    severity: float
    conditions: str
    source: str  # "open-meteo" | "demo"

    def to_dict(self) -> dict:
        return asdict(self)


def _severity_from_weather(precip: float, wind: float) -> float:
    # 0..1 heuristic
    p = min(1.0, precip / 10.0)
    w = min(1.0, wind / 50.0)
    return round(max(p, w), 2)


def _fetch_zone(zone: str) -> dict:
    coords = ZONE_COORDS.get(zone.lower())
    if coords is None:
        # unknown zone → demo
        return {**DEMO_WEATHER.get("central", {}), "source": "demo"}

    url = f"{settings.OPEN_METEO_BASE_URL}/forecast"
    params = {
        "latitude": coords[0],
        "longitude": coords[1],
        "current": "temperature_2m,precipitation,wind_speed_10m",
        "timezone": "UTC",
    }
    try:
        with httpx.Client(timeout=settings.EXTERNAL_TIMEOUT_SECONDS) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json().get("current", {})
        temp = float(data.get("temperature_2m", 0.0))
        precip = float(data.get("precipitation", 0.0))
        wind = float(data.get("wind_speed_10m", 0.0))
        return {
            "temperature_c": temp,
            "precipitation_mm": precip,
            "wind_kph": wind,
            "severity": _severity_from_weather(precip, wind),
            "conditions": "rain" if precip > 0.5 else ("windy" if wind > 20 else "clear"),
            "source": "open-meteo",
        }
    except Exception:  # noqa: BLE001
        fallback = DEMO_WEATHER.get(zone.lower(), DEMO_WEATHER["central"])
        return {**fallback, "source": "demo"}


def get_weather(zone: str) -> WeatherSnapshot:
    key = zone.lower()
    now = time.time()
    cached = _cache.get(key)
    if cached and now - cached[0] < _CACHE_TTL_SECONDS:
        payload = cached[1]
    else:
        payload = _fetch_zone(key)
        _cache[key] = (now, payload)
    return WeatherSnapshot(zone=key, **payload)


def clear_cache() -> None:
    _cache.clear()
