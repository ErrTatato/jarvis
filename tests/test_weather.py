"""
test_weather.py - JARVIS Meteo (Versione funzionante!)
Esegui: python test_weather.py
"""
import requests

# ============================================================================
# CONFIGURAZIONE
# ============================================================================

WEATHER_API_KEY = "295c1eaa1f814ee88a591703252910"  # ← Metti la tua chiave!

print("=" * 80)
print("🌦️  JARVIS - METEO")
print("=" * 80)
print()

if WEATHER_API_KEY == "INSERISCI_QUI_TUA_API_KEY":
    print("❌ ERRORE: Metti la tua API Key nel codice!")
    print("   Registrati su: https://www.weatherapi.com/signup.aspx")
    exit()

print("Comandi: digita città o 'esci'")
print("-" * 80)

# ============================================================================
# FUNZIONE VENTO
# ============================================================================

def get_wind_description(wind_direction, wind_speed):
    """Converte direzione vento in nome italiano"""
    
    wind_names = {
        "N": "Tramontana",
        "NNE": "Tramontana",
        "NE": "Greco",
        "ENE": "Greco",
        "E": "Levante",
        "ESE": "Levante",
        "SE": "Scirocco",
        "SSE": "Ostro",
        "S": "Ostro",
        "SSW": "Libeccio",
        "SW": "Libeccio",
        "WSW": "Ponente",
        "W": "Ponente",
        "WNW": "Maestrale",
        "NW": "Maestrale",
        "NNW": "Tramontana"
    }
    
    if wind_speed < 5:
        return "assenza quasi totale di vento"
    elif wind_speed < 12:
        intensity = "leggera brezza"
    elif wind_speed < 20:
        intensity = "brezza moderata"
    elif wind_speed < 35:
        intensity = "vento sostenuto"
    else:
        intensity = "vento forte"
    
    wind_name = wind_names.get(wind_direction, wind_direction)
    return f"{intensity} da {wind_name}"


def get_weather(city_name):
    """Ottiene meteo dalla API"""
    try:
        url = "http://api.weatherapi.com/v1/current.json"
        params = {
            "key": WEATHER_API_KEY,
            "q": city_name,
            "aqi": "yes",
            "lang": "it"
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 400:
            return None
        
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.Timeout:
        print("❌ Timeout - riprova")
        return None
    except Exception as e:
        print(f"❌ Errore: {e}")
        return None


def format_jarvis_weather(data):
    """Formatta risposta JARVIS"""
    
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
        
        # Location con "nel"
        if region and region != city:
            location = f"a {city} nel {region}"
        else:
            location = f"a {city}"
        
        # Inizio frase
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
        
        # CHIUSURA IRONICA
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
        return f"Errore nell'elaborazione: {e}"


# ============================================================================
# LOOP PRINCIPALE
# ============================================================================

while True:
    city = input("\n📍 Città: ").strip()
    
    if not city:
        continue
    
    if city.lower() in ['esci', 'exit', 'quit', 'q']:
        print("\n👋 Arrivederci signore.")
        break
    
    print(f"\n🔍 Cerco {city}...")
    data = get_weather(city)
    
    print("\n" + "=" * 80)
    print("🎤 JARVIS:")
    print(format_jarvis_weather(data))
    print("=" * 80)
