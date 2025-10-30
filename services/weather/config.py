import os

WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY", "")
WEATHER_API_URL = os.environ.get("WEATHER_API_URL", "https://api.weatherapi.com/v1")
WEATHER_TIMEOUT = int(os.environ.get("WEATHER_TIMEOUT", "10"))
WEATHER_LANGUAGE = os.environ.get("WEATHER_LANGUAGE", "it")
WEATHER_AQI_ENABLED = os.environ.get("WEATHER_AQI_ENABLED", "true").lower() == "true"
