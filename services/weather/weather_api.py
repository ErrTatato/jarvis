"""services/weather/weather_api.py - Connessione API WeatherAPI"""
import requests
from .config import WEATHER_API_KEY, WEATHER_API_URL, WEATHER_TIMEOUT, WEATHER_LANGUAGE, WEATHER_AQI_ENABLED

def get_weather(city_name):
    """Ottiene dati meteo grezzi da WeatherAPI"""
    try:
        params = {
            "key": WEATHER_API_KEY,
            "q": city_name,
            "aqi": "yes" if WEATHER_AQI_ENABLED else "no",
            "lang": WEATHER_LANGUAGE
        }
        
        response = requests.get(WEATHER_API_URL, params=params, timeout=WEATHER_TIMEOUT)
        
        if response.status_code == 400:
            return None
        
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        print(f"[WEATHER] Errore API: {e}")
        return None
