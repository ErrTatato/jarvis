import logging
import httpx
import asyncio
from typing import Dict, Optional

logger = logging.getLogger("JARVIS.Weather")

class WeatherService:
    """Service per meteo"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.openweathermap.org/data/2.5/weather"
    
    async def get_weather(self, location: str = "Milano") -> str:
        """Ottieni meteo per una città"""
        try:
            async with httpx.AsyncClient() as client:
                params = {
                    "q": location,
                    "appid": self.api_key,
                    "units": "metric",
                    "lang": "it"
                }
                
                response = await client.get(self.base_url, params=params, timeout=5.0)
                data = response.json()
                
                if response.status_code == 200:
                    temp = data["main"]["temp"]
                    description = data["weather"][0]["description"]
                    feels_like = data["main"]["feels_like"]
                    humidity = data["main"]["humidity"]
                    
                    return f"A {location}: {description}, {temp}°C. Sensazione: {feels_like}°C, umidità {humidity}%."
                else:
                    return f"Meteo non disponibile per {location}."
        
        except Exception as e:
            logger.error(f"Weather error: {e}")
            return "Sistema meteo offline temporaneamente."