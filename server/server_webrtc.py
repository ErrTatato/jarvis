"""server/server_webrtc.py - JARVIS WebRTC Server FIXED"""

import os
import ssl
import json
import base64
import asyncio
import wave
from pathlib import Path
from io import BytesIO
from aiohttp import web
import aiofiles

from core.jarvis_ai import llm_stream
from core.speak_edge import speak_edge_sync
from config import OPENAI_API_KEY, HOST, PORT, USE_HTTPS

# ============================================================================
# SETUP APP
# ============================================================================

app = web.Application()

# ============================================================================
# HELPER - AUDIO PROCESSING
# ============================================================================

def wav_to_pcm(wav_bytes):
    """Converti WAV a PCM raw"""
    try:
        wav_file = BytesIO(wav_bytes)
        with wave.open(wav_file, 'rb') as wav:
            params = wav.getparams()
            frames = wav.readframes(params.nframes)
            return frames, params
    except Exception as e:
        print(f"[WAV] Errore: {e}")
        return None, None


async def transcribe_audio_with_whisper(audio_bytes: bytes) -> str:
    """Trascrivi audio con Whisper"""
    try:
        from openai import AsyncOpenAI
        
        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        
        # Converti a WAV corretto
        audio_file = BytesIO(audio_bytes)
        audio_file.name = "audio.wav"
        
        # Whisper API
        transcript = await client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language="it",
            prompt="JARVIS Assistant"
        )
        
        text = transcript.text.strip()
        return text if text else "[SILENZIO]"
        
    except Exception as e:
        print(f"[WHISPER] Errore: {e}")
        return "[ERRORE TRASCRIZIONE]"


async def get_jarvis_response(text: str) -> str:
    """Ottieni risposta JARVIS"""
    try:
        if "[ERRORE" in text or "[SILENZIO]" in text:
            return "Mi dispiace, non ho capito bene. Ripeti signore."
        
        response_text = ""
        async for msg_type, content in llm_stream(text):
            if msg_type == "delta":
                response_text += content
        
        return response_text.strip() if response_text.strip() else "Si è verificato un errore tecnico."
        
    except Exception as e:
        print(f"[LLM] Errore: {e}")
        return "Si è verificato un errore tecnico."


async def generate_tts_response(text: str) -> str:
    """Genera TTS e ritorna base64"""
    try:
        print(f"[TTS] Generando audio: {text[:50]}...")
        
        # Usa versione sync
        audio_file = speak_edge_sync(text)
        
        if not audio_file or not Path(audio_file).exists():
            print("[TTS] ❌ Audio file not created")
            return ""
        
        # Leggi e converti a base64
        async with aiofiles.open(audio_file, 'rb') as f:
            audio_bytes = await f.read()
        
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
        
        # Pulizia
        try:
            os.remove(audio_file)
        except:
            pass
        
        return audio_base64
        
    except Exception as e:
        print(f"[TTS] Errore: {e}")
        return ""


# ============================================================================
# ROTTE HTTP
# ============================================================================

async def index(request):
    """Serve index.html"""
    try:
        ui_path = Path(__file__).parent.parent / 'ui' / 'index.html'
        async with aiofiles.open(ui_path, 'r', encoding='utf-8') as f:
            content = await f.read()
        return web.Response(text=content, content_type='text/html')
    except Exception as e:
        print(f"[HTTP] Errore: {e}")
        return web.Response(status=500, text="Errore caricamento UI")


async def process_audio(request):
    """Processa audio ricevuto"""
    try:
        # Leggi audio
        reader = await request.multipart()
        audio_data = None
        
        async for field in reader:
            if field.name == 'audio':
                audio_data = await field.read()
                break
        
        if not audio_data or len(audio_data) < 100:
            return web.json_response({
                'status': 'error',
                'response': 'Audio troppo corto',
                'audio': ''
            })
        
        print(f"[AUDIO] Ricevuti {len(audio_data)} bytes")
        
        # ============================================================================
        # STEP 1: TRASCRIVI
        # ============================================================================
        
        print("[WHISPER] Trascrizione...")
        user_text = await transcribe_audio_with_whisper(audio_data)
        print(f"[WHISPER] → {user_text}")
        
        # ============================================================================
        # STEP 2: RISPOSTA JARVIS
        # ============================================================================
        
        print("[LLM] Elaborando...")
        response_text = await get_jarvis_response(user_text)
        print(f"[LLM] → {response_text[:80]}...")
        
        # ============================================================================
        # STEP 3: TTS
        # ============================================================================
        
        audio_base64 = await generate_tts_response(response_text)
        
        # ============================================================================
        # STEP 4: RITORNA
        # ============================================================================
        
        return web.json_response({
            'status': 'success',
            'transcript': user_text,
            'response': response_text,
            'audio': audio_base64
        })
        
    except Exception as e:
        print(f"[ERROR] {e}")
        return web.json_response({
            'status': 'error',
            'error': str(e),
            'response': 'Errore interno'
        }, status=500)


async def health(request):
    """Health check"""
    return web.json_response({'status': 'ok'})


# ============================================================================
# SETUP ROTTE
# ============================================================================

app.router.add_get('/', index)
app.router.add_post('/process_audio', process_audio)
app.router.add_get('/health', health)

# ============================================================================
# SSL
# ============================================================================

ssl_context = None
if USE_HTTPS:
    cert_file = Path(__file__).parent.parent / 'certs' / 'cert.pem'
    key_file = Path(__file__).parent.parent / 'certs' / 'key.pem'
    
    if cert_file.exists() and key_file.exists():
        try:
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ssl_context.load_cert_chain(str(cert_file), str(key_file))
            print("[SSL] ✅ HTTPS enabled")
        except Exception as e:
            print(f"[SSL] ⚠️  {e}")

# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Avvia server"""
    runner = web.AppRunner(app)
    await runner.setup()
    
    protocol = 'HTTPS' if ssl_context else 'HTTP'
    site = web.TCPSite(runner, HOST, PORT, ssl_context=ssl_context)
    await site.start()
    
    print("=" * 80)
    print("🤖 J.A.R.V.I.S - WebRTC Server")
    print("=" * 80)
    print(f"[SERVER] {protocol} Running on {HOST}:{PORT}")
    print(f"[OpenAI] API: {'✅' if OPENAI_API_KEY else '❌'}")
    print("=" * 80)
    print(f"📱 Accedi: {protocol.lower()}://localhost:{PORT}\n")
    
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        print("\n[SERVER] Shutdown...")
    finally:
        await runner.cleanup()


if __name__ == '__main__':
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())
