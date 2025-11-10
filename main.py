# main.py - VERSIONE COMPLETA CON TUTTE LE FUNZIONALITÀ
import os
import sys
import logging
import asyncio
import argparse
import uvicorn
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent))

try:
    from core.jarvis_ai import JarvisAI
    from services.device_hub import send_command, is_device_connected, list_devices
    from services.weather.weather_api import get_weather
    logger.info("[IMPORT] ✅ Tutti i moduli caricati")
except Exception as e:
    logger.error(f"[IMPORT] ❌ Error: {e}")
    sys.exit(1)

app = FastAPI(title="JARVIS", version="2.3.0")
app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"], 
    allow_credentials=True, 
    allow_methods=["*"], 
    allow_headers=["*"]
)

jarvis = JarvisAI()
device_id = os.environ.get("JARVIS_PRIMARY_DEVICE_ID", "mi13pro")

# Mount ui folder
ui_dir = Path(__file__).parent / "ui"
if ui_dir.exists():
    app.mount("/ui", StaticFiles(directory=ui_dir), name="ui")

# ===== PYDANTIC MODELS =====
class PhoneCall(BaseModel):
    phone: str

class WhatsAppMessage(BaseModel):
    phone: str
    message: str

class WeatherQuery(BaseModel):
    city: str
    unit: str = "metric"  # metric, imperial

# ===== SERVE INDEX.HTML =====
@app.get("/", response_class=FileResponse)
async def serve_index():
    """Serve index.html dalla cartella ui/"""
    return "ui/index.html"

# ===== STATUS & INFO =====
@app.get("/api/status")
async def status():
    try:
        connected = is_device_connected(device_id)
        devices = list_devices()
    except:
        connected = False
        devices = []
    return {
        "status": "running", 
        "device_connected": connected, 
        "device_id": device_id, 
        "active_devices": devices,
        "version": "2.3.0"
    }

@app.get("/api/health")
async def health():
    return {"status": "ok", "timestamp": str(__import__('datetime').datetime.now())}

# ===== WEATHER API =====
@app.get("/api/weather/{city}")
async def weather_endpoint(city: str, unit: str = "metric"):
    """Ottieni il meteo di una città"""
    try:
        weather_data = await get_weather(city, unit)
        return {"status": "ok", "data": weather_data}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ===== PHONE COMMANDS =====
@app.post("/api/device/call")
async def api_call_phone(data: PhoneCall):
    """Chiama un numero"""
    try:
        if not is_device_connected(device_id):
            return {"status": "error", "message": "Device non connesso"}
        logger.info(f"[CALL] Calling {data.phone}")
        result = await send_command(
            device_id, 
            {"type": "command", "action": "call_start", "data": {"phone": data.phone}}
        )
        return result
    except Exception as e:
        logger.error(f"[CALL] Error: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/api/device/call/end")
async def end_call():
    """Termina una chiamata"""
    try:
        if not is_device_connected(device_id):
            return {"status": "error", "message": "Device non connesso"}
        logger.info("[CALL] Ending call")
        result = await send_command(
            device_id, 
            {"type": "command", "action": "call_end", "data": {}}
        )
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ===== WHATSAPP COMMANDS =====
@app.post("/api/device/whatsapp/send")
async def api_whatsapp_send(data: WhatsAppMessage):
    """Invia un messaggio WhatsApp"""
    try:
        if not is_device_connected(device_id):
            return {"status": "error", "message": "Device non connesso"}
        logger.info(f"[WHATSAPP] Sending to {data.phone}: {data.message}")
        result = await send_command(
            device_id, 
            {"type": "command", "action": "whatsapp_send", "data": {"phone": data.phone, "message": data.message}}
        )
        return result
    except Exception as e:
        logger.error(f"[WHATSAPP] Error: {e}")
        return {"status": "error", "message": str(e)}

# ===== NOTIFICATIONS =====
@app.get("/api/device/notifications")
async def api_read_notifications():
    """Leggi le notifiche dal device"""
    try:
        if not is_device_connected(device_id):
            return {"status": "error", "message": "Device non connesso"}
        logger.info("[NOTIFICATIONS] Reading notifications")
        result = await send_command(
            device_id, 
            {"type": "command", "action": "notifications_read", "data": {}}
        )
        return result
    except Exception as e:
        logger.error(f"[NOTIFICATIONS] Error: {e}")
        return {"status": "error", "message": str(e)}

# ===== WEBSOCKET FOR CHAT =====
@app.websocket("/ws/jarvis")
async def websocket_jarvis(websocket: WebSocket):
    """WebSocket per chat testuale con Jarvis"""
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
                    # Elabora il comando
                    response = await jarvis.process_text(user_input, device_id=device_id)
                    await websocket.send_json({"status": "ok", "response": response})
                    logger.info(f"[WEB] Response: {response}")
                except Exception as e:
                    logger.error(f"[WEB] Error: {e}")
                    await websocket.send_json({"status": "error", "message": str(e)})
            
            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})
    
    except WebSocketDisconnect:
        logger.info("[WEB] Client disconnesso")
    except Exception as e:
        logger.error(f"[WEB] Error: {e}")

# ===== VOICE LOOP (OPZIONALE) =====
async def voice_loop():
    """Ascolta wake word 'Jarvis' o tasto PTT (spazio)"""
    try:
        from core.wake_listener import WakeWordListener
        
        wake_listener = WakeWordListener()
        logger.info("[VOICE] Sistema pronto")
        logger.info("[VOICE] - Tieni premuto SPAZIO per PTT")
        logger.info("[VOICE] - Dì 'Jarvis' per wake word")
        
        try:
            while True:
                if wake_listener.listen_for_wake_word():
                    logger.info("[VOICE] Comando riconosciuto!")
                    audio_data = wake_listener.listen_for_command()
                    
                    if audio_data:
                        logger.info(f"[AUDIO] Ricevuti {len(audio_data)} bytes")
                        
                        try:
                            user_input = await jarvis.transcribe_audio(audio_data)
                            
                            if user_input:
                                logger.info(f"[WHISPER] → {user_input}")
                                response = await jarvis.process_text(user_input, device_id=device_id)
                                logger.info(f"[LLM] → {response}")
                                await jarvis.speak_response(response)
                        except Exception as e:
                            logger.error(f"[VOICE] Processing error: {e}")
                
                await asyncio.sleep(0.1)
        except KeyboardInterrupt:
            logger.info("[VOICE] Fermato")
            wake_listener.stop()
    except ImportError:
        logger.error("[VOICE] WakeWordListener non disponibile")
    except Exception as e:
        logger.error(f"[VOICE] Error: {e}")

async def main():
    # Parse CLI args
    parser = argparse.ArgumentParser()
    parser.add_argument("--voice", action="store_true", help="Abilita riconoscimento vocale e PTT")
    args = parser.parse_args()
    enable_voice = args.voice or os.environ.get("JARVIS_VOICE", "").lower() == "1"
    
    logger.info("=" * 80)
    logger.info("🤖 JARVIS - Starting...")
    logger.info("=" * 80)
    
    if os.path.exists("certs/cert.pem") and os.path.exists("certs/key.pem"):
        logger.info("[SSL] ✅ HTTPS enabled")
    else:
        logger.warning("[SSL] ⚠️  Certificati non trovati")
    
    logger.info(f"[CONFIG] Device: {device_id}")
    logger.info("[SERVER] Running on https://0.0.0.0:5000")
    logger.info("[INTERFACE] Open: https://nwe-pasqualini.tail3fb552.ts.net:5000/")
    logger.info("[FEATURES] ✅ Weather, Phone Calls, WhatsApp, Notifications, Voice")
    
    if enable_voice:
        logger.info("[VOICE] ✅ Abilitata (PTT + Wake Word)")
    else:
        logger.info("[VOICE] ⚠️  Disabilitata (usa --voice per abilitare)")
    
    config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=5000,
        log_level="info",
        access_log=False,
        ssl_keyfile="certs/key.pem" if os.path.exists("certs/key.pem") else None,
        ssl_certfile="certs/cert.pem" if os.path.exists("certs/cert.pem") else None,
    )
    server = uvicorn.Server(config)
    
    if enable_voice:
        await asyncio.gather(
            server.serve(),
            voice_loop()
        )
    else:
        await server.serve()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("[EXIT] Goodbye!")
        sys.exit(0)
