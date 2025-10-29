import os
import requests
from typing import Optional

OWM = os.environ.get("OPENWEATHERMAP_KEY", "")

def _coords_or_city(city: Optional[str], lat: Optional[float], lon: Optional[float]):
    if city:
        return {"q": city}
    if lat is not None and lon is not None:
        return {"lat": lat, "lon": lon}
    return {}

def current(city: Optional[str]=None, lat: Optional[float]=None, lon: Optional[float]=None, units: str="metric"):
    if not OWM:
        return {"status": "error", "message": "OPENWEATHERMAP_KEY missing"}
    params = {"appid": OWM, "units": units, **_coords_or_city(city, lat, lon)}
    url = "https://api.openweathermap.org/data/2.5/weather"
    r = requests.get(url, params=params, timeout=10)
    return {"status": "success", "data": r.json()}

def hourly(city: Optional[str]=None, lat: Optional[float]=None, lon: Optional[float]=None, hours: int=48, units: str="metric"):
    if not OWM:
        return {"status": "error", "message": "OPENWEATHERMAP_KEY missing"}
    base = "https://api.openweathermap.org/data/3.0/onecall"
    params = {"appid": OWM, "units": units, "exclude": "minutely,daily,alerts", **_coords_or_city(city, lat, lon)}
    if "q" in params:
        geo = requests.get("http://api.openweathermap.org/geo/1.0/direct", params={"q": params["q"], "limit": 1, "appid": OWM}, timeout=10).json()
        if not geo:
            return {"status": "error", "message": "city not found"}
        params.pop("q", None)
        params["lat"] = geo[0]["lat"]; params["lon"] = geo[0]["lon"]
    r = requests.get(base, params=params, timeout=10).json()
    r["hourly"] = r.get("hourly", [])[:hours]
    return {"status": "success", "data": r}

def daily(city: Optional[str]=None, lat: Optional[float]=None, lon: Optional[float]=None, days: int=7, units: str="metric"):
    if not OWM:
        return {"status": "error", "message": "OPENWEATHERMAP_KEY missing"}
    base = "https://api.openweathermap.org/data/3.0/onecall"
    params = {"appid": OWM, "units": units, "exclude": "minutely,hourly,alerts", **_coords_or_city(city, lat, lon)}
    if "q" in params:
        geo = requests.get("http://api.openweathermap.org/geo/1.0/direct", params={"q": params["q"], "limit": 1, "appid": OWM}, timeout=10).json()
        if not geo:
            return {"status": "error", "message": "city not found"}
        params.pop("q", None)
        params["lat"] = geo[0]["lat"]; params["lon"] = geo[0]["lon"]
    r = requests.get(base, params=params, timeout=10).json()
    r["daily"] = r.get("daily", [])[:days]
    return {"status": "success", "data": r}

def air_quality(lat: float, lon: float):
    if not OWM:
        return {"status": "error", "message": "OPENWEATHERMAP_KEY missing"}
    url = "http://api.openweathermap.org/data/2.5/air_pollution"
    r = requests.get(url, params={"lat": lat, "lon": lon, "appid": OWM}, timeout=10)
    return {"status": "success", "data": r.json()}

def alerts(city: Optional[str]=None, lat: Optional[float]=None, lon: Optional[float]=None):
    if not OWM:
        return {"status": "error", "message": "OPENWEATHERMAP_KEY missing"}
    base = "https://api.openweathermap.org/data/3.0/onecall"
    params = {"appid": OWM, "exclude": "minutely,hourly,daily", **_coords_or_city(city, lat, lon)}
    if "q" in params:
        geo = requests.get("http://api.openweathermap.org/geo/1.0/direct", params={"q": params["q"], "limit": 1, "appid": OWM}, timeout=10).json()
        if not geo:
            return {"status": "error", "message": "city not found"}
        params.pop("q", None)
        params["lat"] = geo[0]["lat"]; params["lon"] = geo[0]["lon"]
    r = requests.get(base, params=params, timeout=10)
    return {"status": "success", "data": r.json().get("alerts", [])}
