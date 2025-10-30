# services/weather/weather_api.py - Connessione API WeatherAPI (compatibile con jarvis_ai)
import os
import math
import requests
from typing import Optional

# Config esterna
from .config import (
    WEATHER_API_KEY,
    WEATHER_API_URL,         # es. "https://api.weatherapi.com/v1"
    WEATHER_TIMEOUT,         # es. 10
    WEATHER_LANGUAGE,        # es. "it"
    WEATHER_AQI_ENABLED      # True/False
)

BASE_URL = (WEATHER_API_URL or "https://api.weatherapi.com/v1").rstrip("/")


def _q_from(city: Optional[str], lat: Optional[float], lon: Optional[float]) -> Optional[str]:
    if city and str(city).strip():
        return str(city).strip()
    if lat is not None and lon is not None:
        return f"{lat},{lon}"
    return None


def _base_params(q: str) -> dict:
    p = {
        "key": WEATHER_API_KEY,
        "q": q,
        "lang": WEATHER_LANGUAGE or "en",
    }
    if WEATHER_AQI_ENABLED:
        p["aqi"] = "yes"
    else:
        p["aqi"] = "no"
    return p


def current(city: Optional[str] = None, lat: Optional[float] = None, lon: Optional[float] = None, units: str = "metric"):
    """
    Meteo attuale via WeatherAPI, con adattamento a OpenWeather-like:
    ritorna {"status":"success","data":{"main":{"temp": <valore>}}}
    """
    try:
        if not WEATHER_API_KEY:
            return {"status": "error", "message": "WEATHER_API_KEY missing"}
        q = _q_from(city, lat, lon)
        if not q:
            return {"status": "error", "message": "Missing city or coordinates"}

        url = f"{BASE_URL}/current.json"
        params = _base_params(q)
        r = requests.get(url, params=params, timeout=WEATHER_TIMEOUT or 10)
        r.raise_for_status()
        j = r.json()

        cur = j.get("current", {}) or {}
        # Compatibilità con jarvis_ai: data.main.temp
        temp = cur.get("temp_c")
        if units and units.lower().startswith("imper"):
            temp = cur.get("temp_f")
        data = {
            "main": {
                "temp": temp
            },
            "raw": j
        }
        return {"status": "success", "data": data}
    except Exception as e:
        return {"status": "error", "message": f"WeatherAPI current error: {e}"}


def hourly(city: Optional[str] = None, lat: Optional[float] = None, lon: Optional[float] = None, hours: int = 48, units: str = "metric"):
    """
    Previsioni orarie via forecast.json; ritorna il payload grezzo e un array 'hourly' tagliato a N ore.
    """
    try:
        if not WEATHER_API_KEY:
            return {"status": "error", "message": "WEATHER_API_KEY missing"}
        q = _q_from(city, lat, lon)
        if not q:
            return {"status": "error", "message": "Missing city or coordinates"}

        days = max(1, min(10, math.ceil(max(1, int(hours)) / 24)))
        url = f"{BASE_URL}/forecast.json"
        params = _base_params(q)
        params["days"] = days
        # alerts non necessario qui; units gestito a consumo (temp_c/temp_f disponibili entrambi)
        r = requests.get(url, params=params, timeout=WEATHER_TIMEOUT or 10)
        r.raise_for_status()
        j = r.json()

        # Estrai prime N ore
        want = max(1, int(hours))
        collected = []
        for day in (j.get("forecast", {}) or {}).get("forecastday", []) or []:
            for h in day.get("hour", []) or []:
                collected.append(h)
                if len(collected) >= want:
                    break
            if len(collected) >= want:
                break

        return {"status": "success", "data": {"hourly": collected, "raw": j}}
    except Exception as e:
        return {"status": "error", "message": f"WeatherAPI hourly error: {e}"}


def daily(city: Optional[str] = None, lat: Optional[float] = None, lon: Optional[float] = None, days: int = 7, units: str = "metric"):
    """
    Previsioni giornaliere via forecast.json; ritorna il payload grezzo e 'daily' (lista di forecastday).
    """
    try:
        if not WEATHER_API_KEY:
            return {"status": "error", "message": "WEATHER_API_KEY missing"}
        q = _q_from(city, lat, lon)
        if not q:
            return {"status": "error", "message": "Missing city or coordinates"}

        days = max(1, min(10, int(days)))
        url = f"{BASE_URL}/forecast.json"
        params = _base_params(q)
        params["days"] = days
        # alerts opzionale qui
        r = requests.get(url, params=params, timeout=WEATHER_TIMEOUT or 10)
        r.raise_for_status()
        j = r.json()

        daily_list = (j.get("forecast", {}) or {}).get("forecastday", []) or []
        return {"status": "success", "data": {"daily": daily_list, "raw": j}}
    except Exception as e:
        return {"status": "error", "message": f"WeatherAPI daily error: {e}"}


def air_quality(lat: float, lon: float):
    """
    Qualità dell'aria (usa current.json con aqi=yes e restituisce current.air_quality).
    """
    try:
        if not WEATHER_API_KEY:
            return {"status": "error", "message": "WEATHER_API_KEY missing"}
        q = _q_from(None, lat, lon)
        if not q:
            return {"status": "error", "message": "Missing coordinates"}

        url = f"{BASE_URL}/current.json"
        params = _base_params(q)
        params["aqi"] = "yes"  # forza aqi
        r = requests.get(url, params=params, timeout=WEATHER_TIMEOUT or 10)
        r.raise_for_status()
        j = r.json()

        aqi = (j.get("current", {}) or {}).get("air_quality", {}) or {}
        return {"status": "success", "data": {"air_quality": aqi, "raw": j}}
    except Exception as e:
        return {"status": "error", "message": f"WeatherAPI AQI error: {e}"}


def alerts(city: Optional[str] = None, lat: Optional[float] = None, lon: Optional[float] = None):
    """
    Allerte meteo: usa forecast.json con alerts=yes (se supportato) e restituisce il blocco 'alerts' se presente.
    """
    try:
        if not WEATHER_API_KEY:
            return {"status": "error", "message": "WEATHER_API_KEY missing"}
        q = _q_from(city, lat, lon)
        if not q:
            return {"status": "error", "message": "Missing city or coordinates"}

        url = f"{BASE_URL}/forecast.json"
        params = _base_params(q)
        params["days"] = 1
        params["alerts"] = "yes"  # dove supportato
        r = requests.get(url, params=params, timeout=WEATHER_TIMEOUT or 10)
        r.raise_for_status()
        j = r.json()

        al = j.get("alerts")
        return {"status": "success", "data": {"alerts": al, "raw": j}}
    except Exception as e:
        return {"status": "error", "message": f"WeatherAPI alerts error: {e}"}

def get_weather(city_name: str):
    """
    Wrapper legacy per compatibilità con vecchi import.
    Ritorna lo stesso schema di current(): {"status":"success","data":{"main":{"temp":...}}}
    """
    return current(city=city_name)
