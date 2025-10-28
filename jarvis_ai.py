"""
jarvis_ai.py - JARVIS ottimizzato (token efficiency)
"""
import os
from typing import AsyncGenerator, Tuple

async def llm_stream(user_message: str) -> AsyncGenerator[Tuple[str, str], None]:
    """
    JARVIS - Versione token-efficiente
    """
    try:
        from openai import AsyncOpenAI
        
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY non configurata")
        
        client = AsyncOpenAI(api_key=api_key)
        model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        
        # ✅ PROMPT COMPRESSO - Solo essenziale!
        system_prompt = """Sei JARVIS, assistente AI di Tony Stark (Iron Man).
Comunica in italiano formale, breve (1-2 frasi), con tono britannico calmo e ironico.
Chiamami "signore". Sii preciso e professionale, mai entusiasta."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        stream = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=100,  # ← Ridotto da 150
            presence_penalty=0.2,  # ← Ridotto
            frequency_penalty=0.2,  # ← Ridotto
            stream=True
        )
        
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield ("delta", chunk.choices[0].delta.content)
        
        yield ("done", "")
        
    except Exception as e:
        print(f"[LLM] ❌ Errore: {e}")
        yield ("done", "")
