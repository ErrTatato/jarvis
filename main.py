# main.py (AGGIORNATO CON PTT + WAKE WORD)
import os
import sys
import logging
import asyncio
import uvicorn
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

sys.path.insert(0, str(Path(__file__).parent))

try:
    from core.jarvis_ai import JarvisAI
    from core.wake_listener import WakeWordListener
    from services.device_hub import send_command, is_device_connected, list_devices
    logger.info("[IMPORT] ✅ Tutti i moduli caricati")
except Exception as e:
    logger.error(f"[IMPORT] ❌ Error: {e}")
    sys.exit(1)

app = FastAPI(title="JARVIS", version="2.3.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

jarvis = JarvisAI()
device_id = os.environ.get("JARVIS_PRIMARY_DEVICE_ID", "mi13pro")

@app.get("/")
async def root():
    return {"status": "running", "version": "2.3.0", "device": device_id}

@app.get("/api/status")
async def status():
    try:
        connected = is_device_connected(device_id)
        devices = list_devices()
    except:
        connected = False
        devices = []
    return {"status": "running", "device_connected": connected, "device_id": device_id, "active_devices": devices}

@app.websocket("/ws/jarvis")
async def websocket_jarvis(websocket: WebSocket):
    await websocket.accept()
    logger.info("[WEB] Client connesso")
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "")
            if msg_type == "chat":
                user_input = data.get("message", "").strip()
                if not user_input:
                    continue
                logger.info(f"[WEB] Input: {user_input}")
                await websocket.send_json({"status": "processing"})
                try:
                    response = await jarvis.process_text(user_input, device_id=device_id)
                    await websocket.send_json({"status": "ok", "response": response})
                except Exception as e:
                    logger.error(f"[WEB] Error: {e}")
                    await websocket.send_json({"status": "error", "message": str(e)})
            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        logger.info("[WEB] Client disconnesso")

@app.post("/api/device/call")
async def api_call_phone(phone: str):
    try:
        if not is_device_connected(device_id):
            return {"status": "error", "message": "Device non connesso"}
        result = await send_command(device_id, {"type": "command", "action": "call_start", "data": {"phone": phone}})
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/device/whatsapp/send")
async def api_whatsapp_send(phone: str, message: str):
    try:
        if not is_device_connected(device_id):
            return {"status": "error", "message": "Device non connesso"}
        result = await send_command(device_id, {"type": "command", "action": "whatsapp_send", "data": {"phone": phone, "message": message}})
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/device/notifications")
async def api_read_notifications():
    try:
        if not is_device_connected(device_id):
            return {"status": "error", "message": "Device non connesso"}
        result = await send_command(device_id, {"type": "command", "action": "notifications_read", "data": {}})
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ===== VOICE LOOP =====
async def voice_loop():
    """Ascolta wake word 'Jarvis' o tasto PTT (spazio)"""
    wake_listener = WakeWordListener(ptt_key='space')  # Spazio = PTT
    logger.info("[VOICE] Sistema pronto:")
    logger.info("[VOICE] - Opzione 1: Tieni premuto SPAZIO e dì 'chiama mamma'")
    logger.info("[VOICE] - Opzione 2: Dì 'Jarvis' poi 'chiama mamma'")
    
    try:
        while True:
            if wake_listener.listen_for_wake_word():
                logger.info("[VOICE] Comando riconosciuto!")
                audio_data = wake_listener.listen_for_command()
                
                if audio_data:
                    logger.info(f"[AUDIO] Ricevuti {len(audio_data)} bytes")
                    user_input = await jarvis.transcribe_audio(audio_data)
                    
                    if user_input:
                        logger.info(f"[WHISPER] → {user_input}")
                        logger.info("[LLM] Elaborando...")
                        response = await jarvis.process_text(user_input, device_id=device_id)
                        logger.info(f"[LLM] → {response}")
                        logger.info("[TTS] Generando risposta...")
                        await jarvis.speak_response(response)
            
            await asyncio.sleep(0.1)
    except KeyboardInterrupt:
        logger.info("[VOICE] Fermato")
        wake_listener.stop()

async def main():
    logger.info("=" * 80)
    logger.info("🤖 JARVIS - Starting...")
    logger.info("=" * 80)
    
    if os.path.exists("certs/cert.pem") and os.path.exists("certs/key.pem"):
        logger.info("[SSL] ✅ HTTPS enabled")
    else:
        logger.warning("[SSL] ⚠️  Certificati non trovati")
    
    logger.info(f"[CONFIG] Device: {device_id}")
    
    config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=5000,
        log_level="info",
        ssl_keyfile="certs/key.pem" if os.path.exists("certs/key.pem") else None,
        ssl_certfile="certs/cert.pem" if os.path.exists("certs/cert.pem") else None,
    )
    server = uvicorn.Server(config)
    
    await asyncio.gather(
        server.serve(),
        voice_loop()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("[EXIT] Goodbye!")
        sys.exit(0)
