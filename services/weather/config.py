"""services/weather/config.py - Configurazione servizio meteo"""
import os

# ✅ Prende dalla variabile di ambiente (NON hardcoded!)
WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY")

# Se non impostata, avvisa
if not WEATHER_API_KEY:
    print("[WEATHER] ⚠️  WEATHER_API_KEY non configurata!")
    print("[WEATHER] Imposta: export WEATHER_API_KEY='tua_chiave'")

WEATHER_API_URL = "http://api.weatherapi.com/v1/current.json"
WEATHER_LANGUAGE = "it"
WEATHER_AQI_ENABLED = True
WEATHER_TIMEOUT = 10
