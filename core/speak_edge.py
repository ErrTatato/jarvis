"""core/speak_edge.py - TTS Edge con fix async"""
import asyncio
import os
import tempfile
import base64
import edge_tts
from pathlib import Path

async def generate_tts_async(text: str, voice: str = "it-IT-DiegoNeural", rate: str = "+0%", pitch: str = "-12Hz"):
    """Genera TTS async"""
    try:
        output_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
        
        # Genera audio
        communicate = edge_tts.Communicate(text, voice=voice, rate=rate, pitch=pitch)
        await communicate.save(output_file)
        
        return output_file
    except Exception as e:
        print(f"[TTS] Errore: {e}")
        return None


def speak_edge_sync(text: str, voice: str = "it-IT-DiegoNeural", rate: str = "+0%", pitch: str = "-12Hz"):
    """Wrapper sync per TTS"""
    try:
        # Crea nuovo event loop se necessario
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(generate_tts_async(text, voice, rate, pitch))
        else:
            # Se loop è già in esecuzione, crea task in thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, generate_tts_async(text, voice, rate, pitch))
                return future.result()
    except Exception as e:
        print(f"[TTS] Errore sync: {e}")
        return None


async def speak_edge(text: str):
    """Main function - usa la versione corretta"""
    return speak_edge_sync(text)
