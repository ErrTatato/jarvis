"""
speak_edge.py - TTS ottimizzato per JARVIS Iron Man
"""
import asyncio
import edge_tts

async def speak_edge_async(text: str, voice: str = "it-IT-DiegoNeural", rate: str = "+0%", pitch: str = "-12Hz"):
    """
    TTS ottimizzato per JARVIS.
    
    Parametri JARVIS:
    - rate="+0%" - Velocità normale (non affrettata, come nel film)
    - pitch="-12Hz" - Voce molto profonda e autorevole
    
    Voci alternative:
    - it-IT-DiegoNeural - Maschio professionale (DEFAULT)
    - it-IT-BenignoNeural - Maschio maturo (più anziano)
    """
    communicate = edge_tts.Communicate(
        text, 
        voice,
        rate=rate,   # Velocità
        pitch=pitch  # Profondità voce
    )
    
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    
    return audio_data

def speak_edge(text: str, output_file: str = None, return_bytes: bool = False, voice: str = None):
    """
    Wrapper sincrono per Edge TTS JARVIS.
    """
    try:
        import os
        
        # Parametri da config
        if voice is None:
            voice = os.environ.get("EDGE_TTS_VOICE", "it-IT-DiegoNeural")
        
        # Parametri JARVIS ottimizzati
        rate = os.environ.get("EDGE_TTS_RATE", "+0%")     # Normale
        pitch = os.environ.get("EDGE_TTS_PITCH", "-12Hz") # Molto profondo
        
        print(f"[TTS] JARVIS - voce '{voice}' rate={rate} pitch={pitch}")
        
        # Event loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Genera
        audio_bytes = loop.run_until_complete(speak_edge_async(text, voice, rate, pitch))
        
        print(f"[TTS] ✅ {len(audio_bytes)} bytes")
        
        if return_bytes:
            return audio_bytes
        
        if output_file:
            from pathlib import Path
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(audio_bytes)
            print(f"[TTS] Salvato: {output_path}")
        
        return None
        
    except Exception as e:
        print(f"[TTS] ❌ Errore: {e}")
        raise
