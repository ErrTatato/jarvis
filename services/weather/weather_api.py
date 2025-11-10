# services/weather/weather_api.py - COMPLETE WEATHER SYSTEM
import aiohttp
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)

WEATHER_API_KEY = "1c1c57a48e3bb1e3faea6509c3fc60d5"  # OpenWeatherMap API Key
WEATHER_API_URL = "https://api.openweathermap.org/data/2.5/weather"
FORECAST_API_URL = "https://api.openweathermap.org/data/2.5/forecast"

async def get_weather(city: str, unit: str = "metric") -> Dict:
    """
    Ottieni il meteo completo di una città
    
    Args:
        city: Nome della città
        unit: 'metric' (Celsius), 'imperial' (Fahrenheit)
    
    Returns:
        Dict con temperatura, umidità, condizioni, vento, etc.
    """
    try:
        params = {
            "q": city,
            "appid": WEATHER_API_KEY,
            "units": unit,
            "lang": "it"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(WEATHER_API_URL, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Estrai i dati principali
                    weather_data = {
                        "city": data.get("name"),
                        "country": data.get("sys", {}).get("country"),
                        "temperature": data.get("main", {}).get("temp"),
                        "feels_like": data.get("main", {}).get("feels_like"),
                        "temp_min": data.get("main", {}).get("temp_min"),
                        "temp_max": data.get("main", {}).get("temp_max"),
                        "humidity": data.get("main", {}).get("humidity"),
                        "pressure": data.get("main", {}).get("pressure"),
                        "description": data.get("weather", [{}])[0].get("description"),
                        "wind_speed": data.get("wind", {}).get("speed"),
                        "wind_deg": data.get("wind", {}).get("deg"),
                        "clouds": data.get("clouds", {}).get("all"),
                        "visibility": data.get("visibility"),
                        "sunrise": data.get("sys", {}).get("sunrise"),
                        "sunset": data.get("sys", {}).get("sunset"),
                        "unit": unit
                    }
                    
                    logger.info(f"[WEATHER] ✅ Weather for {city}: {weather_data['temperature']}°")
                    return weather_data
                else:
                    logger.error(f"[WEATHER] API error: {response.status}")
                    return {"error": f"Weather API error: {response.status}"}
    
    except Exception as e:
        logger.error(f"[WEATHER] Error: {e}")
        return {"error": str(e)}

async def get_forecast(city: str, unit: str = "metric", days: int = 5) -> Dict:
    """
    Ottieni il forecast di 5 giorni
    
    Args:
        city: Nome della città
        unit: 'metric' (Celsius), 'imperial' (Fahrenheit)
        days: Numero di giorni (default 5)
    
    Returns:
        Dict con forecast per i giorni successivi
    """
    try:
        params = {
            "q": city,
            "appid": WEATHER_API_KEY,
            "units": unit,
            "lang": "it",
            "cnt": days * 8  # 8 forecasts al giorno
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(FORECAST_API_URL, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    forecast_list = []
                    for item in data.get("list", []):
                        forecast_list.append({
                            "datetime": item.get("dt_txt"),
                            "temperature": item.get("main", {}).get("temp"),
                            "description": item.get("weather", [{}])[0].get("description"),
                            "humidity": item.get("main", {}).get("humidity"),
                            "wind_speed": item.get("wind", {}).get("speed"),
                            "rain_prob": item.get("pop", 0) * 100
                        })
                    
                    logger.info(f"[FORECAST] ✅ Forecast for {city}: {len(forecast_list)} entries")
                    return {"city": city, "forecasts": forecast_list}
                else:
                    logger.error(f"[FORECAST] API error: {response.status}")
                    return {"error": f"Forecast API error: {response.status}"}
    
    except Exception as e:
        logger.error(f"[FORECAST] Error: {e}")
        return {"error": str(e)}

def format_weather_response(weather: Dict, unit: str = "metric") -> str:
    """Formatta il meteo in stringa leggibile"""
    if "error" in weather:
        return f"Errore nel recupero del meteo: {weather['error']}"
    
    temp_symbol = "°C" if unit == "metric" else "°F"
    
    response = f"""
Meteo a {weather.get('city', 'N/A')}, {weather.get('country', 'N/A')}:
🌡️  Temperatura: {weather.get('temperature', 'N/A')}{temp_symbol}
🤔 Percepita: {weather.get('feels_like', 'N/A')}{temp_symbol}
📊 Min/Max: {weather.get('temp_min', 'N/A')}{temp_symbol} / {weather.get('temp_max', 'N/A')}{temp_symbol}
💨 Vento: {weather.get('wind_speed', 'N/A')} m/s ({weather.get('wind_deg', 'N/A')}°)
💧 Umidità: {weather.get('humidity', 'N/A')}%
☁️  Copertura nuvolosa: {weather.get('clouds', 'N/A')}%
📋 Condizioni: {weather.get('description', 'N/A')}
"""
    return response.strip()
