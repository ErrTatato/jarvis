
import logging
import aiohttp
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class WeatherAPI:
    """API per ottenere dati meteo da OpenWeatherMap"""
    
    def __init__(self, api_key: str = "2e29a6e3821f1e3f53e34bb9fec4e0d4"):
        """
        Inizializza WeatherAPI
        api_key: chiave API di OpenWeatherMap (gratuita)
        """
        self.api_key = api_key
        self.base_url = "https://api.openweathermap.org/data/2.5/weather"
        self.session = None
    
    async def get_weather(self, city: str, units: str = "metric", lang: str = "it") -> Dict[str, Any]:
        """
        Ottiene il meteo per una città
        
        Args:
            city: Nome della città (es: "Roma", "Milano")
            units: "metric" per Celsius, "imperial" per Fahrenheit
            lang: Lingua della risposta ("it", "en", ecc)
        
        Returns:
            Dict con status e dati meteo
        """
        try:
            # Crea sessione se non esiste
            if self.session is None:
                self.session = aiohttp.ClientSession()
            
            # Parametri query
            params = {
                "q": city,
                "appid": self.api_key,
                "units": units,
                "lang": lang
            }
            
            logger.info(f"[WEATHER] Requesting: {city}")
            
            async with self.session.get(self.base_url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    # Estrai i dati rilevanti
                    weather_data = {
                        "city": data.get("name"),
                        "country": data.get("sys", {}).get("country"),
                        "temperature": data.get("main", {}).get("temp"),
                        "feels_like": data.get("main", {}).get("feels_like"),
                        "temp_min": data.get("main", {}).get("temp_min"),
                        "temp_max": data.get("main", {}).get("temp_max"),
                        "pressure": data.get("main", {}).get("pressure"),
                        "humidity": data.get("main", {}).get("humidity"),
                        "wind_speed": data.get("wind", {}).get("speed"),
                        "wind_deg": data.get("wind", {}).get("deg"),
                        "clouds": data.get("clouds", {}).get("all"),
                        "description": data.get("weather", [{}])[0].get("main", ""),
                        "details": data.get("weather", [{}])[0].get("description", ""),
                        "visibility": data.get("visibility", 0) / 1000 if data.get("visibility") else 0,  # Converti in km
                        "rain": data.get("rain", {}).get("1h", 0),
                        "snow": data.get("snow", {}).get("1h", 0),
                        "sunrise": data.get("sys", {}).get("sunrise"),
                        "sunset": data.get("sys", {}).get("sunset"),
                        "timezone": data.get("timezone")
                    }
                    
                    logger.info(f"[WEATHER] ✅ Got weather for {city}: {weather_data['temperature']}°C")
                    
                    return {
                        "status": "success",
                        "data": weather_data
                    }
                
                elif resp.status == 404:
                    logger.warning(f"[WEATHER] ❌ City not found: {city}")
                    return {
                        "status": "error",
                        "response": f"❌ Città non trovata: {city}"
                    }
                
                else:
                    logger.error(f"[WEATHER] Error {resp.status}: {await resp.text()}")
                    return {
                        "status": "error",
                        "response": f"❌ Errore API: {resp.status}"
                    }
        
        except asyncio.TimeoutError:
            logger.error(f"[WEATHER] Timeout")
            return {
                "status": "error",
                "response": "❌ Timeout - Prova di nuovo"
            }
        
        except Exception as e:
            logger.error(f"[WEATHER] Error: {e}")
            return {
                "status": "error",
                "response": f"❌ Errore: {str(e)}"
            }
    
    async def close(self):
        """Chiudi la sessione"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def format_weather(self, city: str) -> str:
        """
        Formatta il meteo in modo leggibile
        """
        result = await self.get_weather(city)
        
        if result["status"] != "success":
            return result["response"]
        
        data = result["data"]
        
        response = (
            f"🌤️ **{data['city']}, {data['country']}**\n"
            f"🌡️ Temperatura: {data['temperature']}°C (percepita: {data['feels_like']}°C)\n"
            f"Min/Max: {data['temp_min']}°C / {data['temp_max']}°C\n"
            f"💧 Umidità: {data['humidity']}%\n"
            f"💨 Vento: {data['wind_speed']} m/s\n"
            f"☁️ Nuvolosità: {data['clouds']}%\n"
            f"👁️ Visibilità: {data['visibility']:.1f} km\n"
            f"📝 Condizioni: {data['details'].capitalize()}\n"
            f"🌅 Sunrise: {data['sunrise']} | 🌇 Sunset: {data['sunset']}"
        )
        
        if data['rain'] > 0:
            response += f"\n🌧️ Pioggia (1h): {data['rain']} mm"
        
        if data['snow'] > 0:
            response += f"\n❄️ Neve (1h): {data['snow']} mm"
        
        return response


# Importa asyncio per gestire timeout
import asyncio