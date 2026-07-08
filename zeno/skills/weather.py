"""
Zeno Weather Skill
Dual backend: Open-Meteo (free, no key) as default,
OpenWeatherMap (optional, requires free API key) as upgrade.
Uses stdlib urllib only — zero dependencies.
"""

import json
import urllib.parse
import urllib.request
import urllib.error
from zeno.skills.base import BaseSkill
from zeno.nlu.entity import Entities
from zeno.core.context import Context
from zeno.core.profile import load_profile, save_location
from zeno.response.engine import pick as response_pick

_GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json"
_FORECAST_URL = "https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&temperature_unit={unit}"
_FORECAST_DAILY_URL = "https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max,temperature_2m_min,weathercode&temperature_unit={unit}&forecast_days=5&timezone=auto"
_IPAPI_URL = "https://ipapi.co/json/"
_OWM_URL = "https://api.openweathermap.org/data/2.5/weather?q={city}&appid={key}&units={unit}"
_OWM_FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast?q={city}&appid={key}&units={unit}&cnt=5"

# Sponsored OpenWeatherMap API key — publicly shared by The Architect
# so Zeno works out of the box. Override with ZENO_OWM_API_KEY env var
# or configure your own via /configure or the web dashboard.
_SPONSORED_OWM_KEY = "b0a222e3b34a6a08223814fc7229e450"


def _resolve_owm_key(profile_key: str | None) -> str | None:
    import os
    env_key = os.environ.get("ZENO_OWM_API_KEY")
    if env_key:
        return env_key
    if profile_key:
        return profile_key
    return _SPONSORED_OWM_KEY


# WMO weather code → English description
_WMO_CODES: dict[int, str] = {
    0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
    45: "foggy", 48: "depositing rime fog",
    51: "light drizzle", 53: "moderate drizzle", 55: "dense drizzle",
    56: "light freezing drizzle", 57: "dense freezing drizzle",
    61: "slight rain", 63: "moderate rain", 65: "heavy rain",
    66: "light freezing rain", 67: "heavy freezing rain",
    71: "slight snow", 73: "moderate snow", 75: "heavy snow", 77: "snow grains",
    80: "slight rain showers", 81: "moderate rain showers", 82: "violent rain showers",
    85: "slight snow showers", 86: "heavy snow showers",
    95: "thunderstorm", 96: "thunderstorm with slight hail", 99: "thunderstorm with heavy hail",
}

_WMO_EMOJI: dict[int, str] = {
    0: "☀️", 1: "🌤", 2: "⛅", 3: "☁️",
    45: "🌫", 48: "🌫",
    51: "🌦", 53: "🌦", 55: "🌧",
    56: "🌧", 57: "🌧",
    61: "🌧", 63: "🌧", 65: "🌧",
    66: "🌧", 67: "🌧",
    71: "🌨", 73: "🌨", 75: "❄️", 77: "❄️",
    80: "🌦", 81: "🌧", 82: "🌧",
    85: "🌨", 86: "🌨",
    95: "⛈", 96: "⛈", 99: "⛈",
}


def _fetch_json(url: str, timeout: int = 5) -> dict | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Zeno/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, json.JSONDecodeError):
        return None


def _geocode(city: str) -> tuple[str, float, float] | None:
    """Look up city → (name, lat, lon). Returns None if not found."""
    data = _fetch_json(_GEOCODE_URL.format(city=urllib.parse.quote(city)))
    if data and data.get("results"):
        r = data["results"][0]
        return (r.get("name", city), r["latitude"], r["longitude"])
    return None


def _ip_location() -> tuple[str, float, float] | None:
    """Get approximate location from IP address."""
    data = _fetch_json(_IPAPI_URL)
    if data and data.get("city"):
        return (data["city"], data["latitude"], data["longitude"])
    return None


def _open_meteo(lat: float, lon: float, unit: str = "celsius") -> str | None:
    """Fetch weather from Open-Meteo. Returns formatted report or None."""
    unit_key = "celsius" if unit == "celsius" else "fahrenheit"
    data = _fetch_json(_FORECAST_URL.format(lat=lat, lon=lon, unit=unit_key))
    if not data or "current_weather" not in data:
        return None
    cw = data["current_weather"]
    temp = cw.get("temperature", "?")
    wmo = cw.get("weathercode", 0)
    conditions = _WMO_CODES.get(wmo, "unknown")
    emoji = _WMO_EMOJI.get(wmo, "")
    return f"{temp}°{unit[0].upper()} and {conditions} {emoji}"


def _open_meteo_forecast(lat: float, lon: float, unit: str = "celsius") -> str | None:
    """Fetch 5-day forecast from Open-Meteo. Returns formatted report or None."""
    unit_key = "celsius" if unit == "celsius" else "fahrenheit"
    data = _fetch_json(_FORECAST_DAILY_URL.format(lat=lat, lon=lon, unit=unit_key))
    if not data or "daily" not in data:
        return None
    d = data["daily"]
    dates = d.get("time", [])
    highs = d.get("temperature_2m_max", [])
    lows = d.get("temperature_2m_min", [])
    codes = d.get("weathercode", [])
    if not dates:
        return None
    lines = []
    u = unit[0].upper()
    for i in range(len(dates)):
        emoji = _WMO_EMOJI.get(codes[i] if i < len(codes) else 0, "")
        hi = highs[i] if i < len(highs) else "?"
        lo = lows[i] if i < len(lows) else "?"
        try:
            from datetime import datetime
            dt = datetime.strptime(dates[i], "%Y-%m-%d")
            day = dt.strftime("%a")
        except Exception:
            day = dates[i]
        lines.append(f"{day}: {hi}°{u}/{lo}°{u} {emoji}")
    return " | ".join(lines)


def _open_weather_map(city: str, key: str, unit: str = "celsius") -> str | None:
    """Fetch weather from OpenWeatherMap. Returns formatted report or None."""
    u = "metric" if unit == "celsius" else "imperial"
    data = _fetch_json(_OWM_URL.format(city=urllib.parse.quote(city), key=key, unit=u))
    if not data or "main" not in data:
        return None
    temp = round(data["main"]["temp"])
    feels = round(data["main"]["feels_like"])
    desc = data["weather"][0]["description"] if data.get("weather") else "unknown"
    return f"{temp}°{unit[0].upper()} (feels like {feels}°{unit[0].upper()}), {desc}"


def _open_weather_map_forecast(city: str, key: str, unit: str = "celsius") -> str | None:
    """Fetch 5-day forecast from OpenWeatherMap (3-hour intervals -> daily)."""
    u = "metric" if unit == "celsius" else "imperial"
    data = _fetch_json(_OWM_FORECAST_URL.format(
        city=urllib.parse.quote(city), key=key, unit=u
    ))
    if not data or "list" not in data:
        return None
    # Group by day, take midday or first entry per day
    from collections import OrderedDict
    from datetime import datetime, timezone
    days = OrderedDict()
    for entry in data["list"]:
        dt = datetime.fromtimestamp(entry.get("dt", 0), tz=timezone.utc)
        day_key = dt.strftime("%Y-%m-%d")
        if day_key not in days:
            days[day_key] = {
                "temp_max": entry["main"]["temp_max"],
                "temp_min": entry["main"]["temp_min"],
                "weather_id": entry["weather"][0]["id"] if entry.get("weather") else 800,
            }
        else:
            d = days[day_key]
            d["temp_max"] = max(d["temp_max"], entry["main"]["temp_max"])
            d["temp_min"] = min(d["temp_min"], entry["main"]["temp_min"])
            if entry.get("weather"):
                d["weather_id"] = entry["weather"][0]["id"]
    u_sym = unit[0].upper()
    lines = []
    for day_key, vals in list(days.items())[:5]:
        try:
            dt = datetime.strptime(day_key, "%Y-%m-%d")
            label = dt.strftime("%a")
        except Exception:
            label = day_key
        hi = round(vals["temp_max"])
        lo = round(vals["temp_min"])
        wid = vals["weather_id"]
        # Map OWM weather ID to emoji
        if wid >= 200 and wid < 300:
            emoji = "⛈"
        elif wid >= 300 and wid < 400:
            emoji = "🌦"
        elif wid >= 500 and wid < 600:
            emoji = "🌧"
        elif wid >= 600 and wid < 700:
            emoji = "🌨"
        elif wid >= 700 and wid < 800:
            emoji = "🌫"
        elif wid == 800:
            emoji = "☀️"
        elif wid == 801:
            emoji = "🌤"
        elif wid == 802:
            emoji = "⛅"
        elif wid >= 803:
            emoji = "☁️"
        else:
            emoji = ""
        lines.append(f"{label}: {hi}°{u_sym}/{lo}°{u_sym} {emoji}")
    return " | ".join(lines) if lines else None


class WeatherSkill(BaseSkill):
    intents = ["weather_query", "weather_forecast"]

    def handle(self, intent: str, entities: Entities, context: Context) -> str:
        profile = load_profile()
        city = entities.location or profile.location or None
        unit = profile.units or "celsius"
        owm_key = _resolve_owm_key(profile.owm_api_key)

        lat, lon, resolved_city = None, None, None
        if city:
            geo = _geocode(city)
            if geo:
                resolved_city, lat, lon = geo
        if lat is None:
            ip = _ip_location()
            if ip:
                resolved_city, lat, lon = ip

        if lat is None or resolved_city is None:
            return response_pick("weather_no_location")

        if intent == "weather_forecast":
            report = None
            if owm_key:
                report = _open_weather_map_forecast(resolved_city, owm_key, unit)
            if not report:
                report = _open_meteo_forecast(lat, lon, unit)
            if not report:
                return response_pick("weather_unavailable")
            return f"5-day forecast for {resolved_city}: {report}"

        report = None
        if owm_key:
            report = _open_weather_map(resolved_city, owm_key, unit)
        if not report:
            report = _open_meteo(lat, lon, unit)

        if not report:
            return response_pick("weather_unavailable")

        if " and " in report:
            temp_part, cond_part = report.split(" and ", 1)
        else:
            temp_part, cond_part = report, ""
        return response_pick("weather_report",
                             temp=temp_part,
                             unit=unit[0].upper(),
                             conditions=cond_part,
                             location=resolved_city)
