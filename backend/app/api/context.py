from datetime import date

from fastapi import APIRouter, Query
from app.integrations import holiday_client, weather_client


router = APIRouter(prefix="/context", tags=["context"])


@router.get("/weather")
def weather(zone: str = Query(default="central")):
    return weather_client.get_weather(zone).to_dict()


@router.get("/holidays")
def holidays(country: str | None = Query(default=None), year: int | None = Query(default=None)):
    effective_country = (country or "ET").upper()
    effective_year = year or date.today().year
    return {
        "country": effective_country,
        "year": effective_year,
        "holidays": holiday_client.get_holidays(effective_country, effective_year),
    }
