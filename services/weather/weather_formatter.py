"""services/weather/weather_formatter.py - Formattazione risposte JARVIS"""

from .weather_utils import get_wind_description

def format_jarvis_weather_basic(data):
    """Risposta meteo concisa e ironica"""
    
    if not data:
        return "Mi dispiace signore, quella città sembra non esistere nella realtà, evidentemente."
    
    try:
        loc = data["location"]
        curr = data["current"]
        
        city = loc["name"]
        region = loc.get("region", "")
        temp = int(curr["temp_c"])
        condition = curr["condition"]["text"].lower()
        wind = curr["wind_kph"]
        wind_dir = curr["wind_dir"]
        rain_chance = curr.get("daily_chance_of_rain", 0) if "daily_chance_of_rain" in curr else 0
        precip = curr["precip_mm"]
        uv = curr["uv"]
        
        # Location
        if region and region != city:
            location = f"a {city} nel {region}"
        else:
            location = f"a {city}"
        
        # Frase principale
        response = f"Le condizioni meteo attuali {location} prevedono "
        response += f"cielo {condition} a {temp} gradi"
        
        # Vento
        if wind > 5:
            wind_desc = get_wind_description(wind_dir, wind)
            response += f", con {wind_desc}"
        
        # Pioggia
        if precip > 1:
            response += f", pioggia {precip:.1f}mm"
        elif rain_chance > 55:
            response += f", {rain_chance}% di probabilità di pioggia"
        
        response += ", signore. "
        
        # Chiusura ironica
        if condition in ["sereno", "soleggiato"]:
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
        return f"Errore: {e}"


def format_jarvis_weather_detailed(data, detail_type="all"):
    """Risposta meteo dettagliata e telegrafica"""
    
    if not data:
        return "Dati non disponibili."
    
    try:
        loc = data["location"]
        curr = data["current"]
        
        city = loc["name"]
        region = loc.get("region", "")
        humidity = curr["humidity"]
        wind = curr["wind_kph"]
        wind_dir = curr["wind_dir"]
        wind_gust = curr.get("gust_kph", 0)
        uv = curr["uv"]
        visibility = curr["vis_km"]
        pressure = curr["pressure_mb"]
        cloud = curr["cloud"]
        precip = curr["precip_mm"]
        feels = int(curr["feelslike_c"])
        
        # Location
        if region and region != city:
            location = f"{city}, {region}"
        else:
            location = city
        
        response = f"Dettagli meteo per {location}:\n"
        
        if detail_type in ["all", "humidity"]:
            response += f"• Umidità: {humidity}%\n"
        
        if detail_type in ["all", "uv"]:
            response += f"• Indice UV: {uv} "
            if uv < 3:
                response += "(basso)\n"
            elif uv < 6:
                response += "(moderato)\n"
            elif uv < 8:
                response += "(elevato)\n"
            else:
                response += "(molto elevato)\n"
        
        if detail_type in ["all", "wind"]:
            response += f"• Vento: {wind:.0f} km/h da {wind_dir}"
            if wind_gust > wind:
                response += f" (raffiche {wind_gust:.0f} km/h)"
            response += "\n"
        
        if detail_type in ["all", "visibility"]:
            response += f"• Visibilità: {visibility:.1f} km\n"
        
        if detail_type in ["all", "pressure"]:
            response += f"• Pressione: {pressure:.0f} mb\n"
        
        if detail_type == "all":
            response += f"• Temperatura percepita: {feels}°C\n"
            response += f"• Nuvolosità: {cloud}%\n"
            response += f"• Precipitazioni: {precip:.1f}mm"
        
        return response.rstrip()
        
    except Exception as e:
        return f"Errore: {e}"
