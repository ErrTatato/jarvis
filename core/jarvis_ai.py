"""core/jarvis_ai.py - LLM Core JARVIS con Weather Integration"""
import os
import json
from typing import AsyncGenerator, Tuple
from services.weather import get_weather, format_jarvis_weather_basic, format_jarvis_weather_detailed, get_weather_function_definition

async def llm_stream(user_message: str) -> AsyncGenerator[Tuple[str, str], None]:
    """JARVIS LLM Stream con Function Calling"""
    try:
        from openai import AsyncOpenAI
        
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY non configurata")
        
        client = AsyncOpenAI(api_key=api_key)
        model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        
        system_prompt = """Sei JARVIS, assistente AI di Tony Stark (Iron Man).
Comunica in italiano formale, breve (1-2 frasi), con tono britannico calmo e ironico.
Chiamami "signore". Sii preciso e professionale, mai entusiasta.

Se l'utente chiede il meteo o informazioni meteorologiche, usa la funzione get_weather.
Se chiede dettagli tecnici (umidità, UV, vento, ecc.), usa get_weather_details."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        # Function definitions
        tools = get_weather_function_definition()
        
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=0.7,
            max_tokens=150
        )
        
        # Gestisci function calls
        if response.choices[0].finish_reason == "tool_calls":
            for tool_call in response.choices[0].message.tool_calls:
                args = json.loads(tool_call.function.arguments)
                
                if tool_call.function.name == "get_current_weather":
                    weather_data = get_weather(args.get("city", ""))
                    if weather_data:
                        result = format_jarvis_weather_basic(weather_data)
                        yield ("delta", result)
                        yield ("done", "")
                        return
                
                elif tool_call.function.name == "get_weather_details":
                    weather_data = get_weather(args.get("city", ""))
                    if weather_data:
                        result = format_jarvis_weather_detailed(weather_data, args.get("detail_type", "all"))
                        yield ("delta", result)
                        yield ("done", "")
                        return
        
        # Risposta normale
        stream = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=100,
            stream=True
        )
        
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield ("delta", chunk.choices[0].delta.content)
        
        yield ("done", "")
        
    except Exception as e:
        print(f"[LLM] Errore: {e}")
        yield ("error", str(e))
        yield ("done", "")
