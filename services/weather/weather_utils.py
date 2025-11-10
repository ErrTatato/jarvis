# services/weather/weather_utils.py
def get_wind_description(wind_direction: str, wind_speed: float) -> str:
    """Converte direzione vento in nome italiano"""
    wind_names = {
        "N": "Tramontana", "NNE": "Tramontana", "NE": "Greco", "ENE": "Greco",
        "E": "Levante", "ESE": "Levante", "SE": "Scirocco", "SSE": "Ostro",
        "S": "Ostro", "SSW": "Libeccio", "SW": "Libeccio", "WSW": "Ponente",
        "W": "Ponente", "WNW": "Maestrale", "NW": "Maestrale", "NNW": "Tramontana"
    }
    
    if wind_speed < 5:
        intensity = "assenza quasi totale di vento"
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
