"""services/weather/weather_functions.py - Function calling definitions"""

def get_weather_function_definition():
    """Ritorna definizione funzioni per GPT"""
    return [
        {
            "type": "function",
            "function": {
                "name": "get_current_weather",
                "description": "Ottiene condizioni meteo attuali per una città",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {
                            "type": "string",
                            "description": "Nome della città"
                        }
                    },
                    "required": ["city"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_weather_details",
                "description": "Ottiene dettagli tecnici meteo specifici",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {
                            "type": "string",
                            "description": "Nome della città"
                        },
                        "detail_type": {
                            "type": "string",
                            "enum": ["humidity", "uv", "wind", "visibility", "pressure", "all"],
                            "description": "Tipo di dettaglio richiesto"
                        }
                    },
                    "required": ["city", "detail_type"]
                }
            }
        }
    ]
