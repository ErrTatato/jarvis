# services/weather/weather_formatter.py
from .weather_utils import get_wind_description

def format_jarvis_weather_basic(data):
    """Risposta meteo concisa e ironica"""
    if not data or not isinstance(data, dict):
        return "Mi dispiace signore, quella città sembra non esistere nella realtà, evidentemente."
    try:
        loc = data.get("location", {})
        cur = data.get("current", {})
        
        if not loc or not cur:
            return "Dati meteo incompleti."
        
        city = loc.get("name", "Somewhere")
        region = loc.get("region", "")
        temp = int(cur.get("temp_c", 20))
        condition = cur.get("condition", {}).get("text", "tempo ignoto").lower()
        wind = cur.get("wind_kph", 0)
        wind_dir = cur.get("wind_dir", "N")
        precip = cur.get("precip_mm", 0)
        uv = cur.get("uv", 0)
        
        location = f"a {city} nel {region}" if region and region != city else f"a {city}"
        response = f"Le condizioni meteo attuali {location} prevedono cielo {condition} a {temp}°C"
        
        if wind > 5:
            wind_desc = get_wind_description(wind_dir, wind)
            response += f", con {wind_desc}"
        
        if precip > 1:
            response += f", pioggia {precip:.1f}mm"
        
        response += ", signore. "
        
        if "sereno" in condition or "soleggiato" in condition:
            if wind > 25:
                response += "Giornata splendida per non uscire. Il vento potrebbe rovinarvi l'acconciatura."
            else:
                response += "Giornata splendida, almeno meteo."
        elif "pioggia" in condition or "temporale" in condition:
            if precip > 5:
                response += "Purtroppo le previsioni erano puntuali."
            else:
                response += "Consiglio un ombrello, a meno che ami stare in umido."
        elif "neve" in condition:
            response += "Condizioni da sciare. O semplicemente da stare in casa."
        elif uv > 7:
            response += "UV pericoloso. Non vorrete diventare aragosta, vero?"
        else:
            response += "Una giornata come tante altre."
        
        return response
    except Exception as e:
        return f"Errore nel parsing meteo: {e}"

def format_jarvis_weather_detailed(data, detail_type="all"):
    """Risposta meteo dettagliata"""
    if not data or not isinstance(data, dict):
        return "Dati non disponibili."
    try:
        loc = data.get("location", {})
        cur = data.get("current", {})
        
        if not loc or not cur:
            return "Dati meteo incompleti."
        
        city = loc.get("name", "Somewhere")
        region = loc.get("region", "")
        location = f"{city}, {region}" if region and region != city else city
        
        response = f"Dettagli meteo per {location}:\n"
        
        humidity = cur.get("humidity", 0)
        wind = cur.get("wind_kph", 0)
        wind_dir = cur.get("wind_dir", "N")
        wind_gust = cur.get("gust_kph", wind)
        uv = cur.get("uv", 0)
        vis = cur.get("vis_km", 10)
        pressure = cur.get("pressure_mb", 1013)
        cloud = cur.get("cloud", 0)
        precip = cur.get("precip_mm", 0)
        feels = int(cur.get("feelslike_c", 20))
        
        if detail_type in ["all", "humidity"]:
            response += f"• Umidità: {humidity}%\n"
        if detail_type in ["all", "uv"]:
            uv_level = "basso" if uv < 3 else "moderato" if uv < 6 else "elevato" if uv < 8 else "molto elevato"
            response += f"• Indice UV: {uv} ({uv_level})\n"
        if detail_type in ["all", "wind"]:
            gust_str = f" (raffiche {wind_gust:.0f} km/h)" if wind_gust > wind else ""
            response += f"• Vento: {wind:.0f} km/h da {wind_dir}{gust_str}\n"
        if detail_type in ["all", "visibility"]:
            response += f"• Visibilità: {vis:.1f} km\n"
        if detail_type in ["all", "pressure"]:
            response += f"• Pressione: {pressure:.0f} mb\n"
        if detail_type == "all":
            response += f"• Temperatura percepita: {feels}°C\n"
            response += f"• Nuvolosità: {cloud}%\n"
            response += f"• Precipitazioni: {precip:.1f}mm"
        
        return response.rstrip()
    except Exception as e:
        return f"Errore: {e}"
