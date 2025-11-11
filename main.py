import os
import sys
import logging
import asyncio
import argparse
import uvicorn
import ssl
from pathlib import Path

# ===== SETUP LOGGING =====
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# ===== IMPORTS =====
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import json

# ===== ADD PATH =====
sys.path.insert(0, str(Path(__file__).parent))

# ===== IMPORT CORE MODULES =====
try:
    from core.jarvis_ai import JarvisAI
    from services.device_hub import DeviceHub
    from services.weather.weather_api import WeatherAPI
    logger.info("[IMPORT] ✅ Tutti i moduli caricati")
except Exception as e:
    logger.error(f"[IMPORT] ❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ===== FASTAPI APP =====
app = FastAPI(
    title="JARVIS - Voice Assistant",
    version="2.3.0",
    description="AI Voice Assistant with Phone, WhatsApp, Weather, Notifications"
)

# ===== CORS MIDDLEWARE =====
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# ===== GLOBALS =====
jarvis = JarvisAI()
device_hub = DeviceHub()
weather_api = WeatherAPI()
jarvis.set_device_hub(device_hub)

device_id = os.environ.get("JARVIS_PRIMARY_DEVICE_ID", "mi13pro")

# ===== MOUNT UI FOLDER =====
ui_dir = Path(__file__).parent / "ui"
if ui_dir.exists():
    try:
        app.mount("/static", StaticFiles(directory=ui_dir, html=True), name="static")
        logger.info(f"[UI] ✅ Mounted ui folder from {ui_dir}")
    except Exception as e:
        logger.warning(f"[UI] ⚠️  Could not mount ui folder: {e}")

# ===== PYDANTIC MODELS =====
class PhoneCall(BaseModel):
    phone: str
    contact_name: str = None

class WhatsAppMessage(BaseModel):
    phone: str
    message: str
    contact_name: str = None

class WeatherQuery(BaseModel):
    city: str
    unit: str = "metric"

class TextCommand(BaseModel):
    message: str
    device_id: str = None

# ===== SERVE INDEX.HTML =====
@app.get("/", response_class=FileResponse)
async def serve_index():
    """Serve index.html dalla cartella ui/"""
    index_path = ui_dir / "index.html"
    if index_path.exists():
        return index_path
    return {"status": "JARVIS v2.3.0 - Running"}

@app.get("/index.html", response_class=FileResponse)
async def serve_index_direct():
    """Serve index.html direttamente"""
    index_path = ui_dir / "index.html"
    if index_path.exists():
        return index_path
    return {"status": "JARVIS v2.3.0"}

# ===== STATUS & INFO =====
@app.get("/api/status")
async def status():
    """Status della API e device connessi"""
    try:
        devices = device_hub.list_devices()
        connected = device_id in devices if devices else False
    except:
        connected = False
        devices = []
    
    return {
        "status": "running",
        "version": "2.3.0",
        "device_connected": connected,
        "device_id": device_id,
        "active_devices": devices,
        "timestamp": str(__import__('datetime').datetime.now())
    }

@app.get("/api/health")
async def health():
    """Health check"""
    return {
        "status": "ok",
        "timestamp": str(__import__('datetime').datetime.now())
    }

# ===== WEATHER API =====
@app.get("/api/weather/{city}")
async def weather_endpoint(city: str, unit: str = "metric"):
    """Ottieni il meteo di una città"""
    try:
        logger.info(f"[WEATHER] Richiesta per {city}")
        result = await weather_api.get_weather(city, unit)
        return result
    except Exception as e:
        logger.error(f"[WEATHER] Error: {e}")
        return {
            "status": "error",
            "response": f"❌ Errore meteo: {str(e)}"
        }

# ===== DEVICE REGISTRATION =====
@app.get("/api/device/register")
async def register_device(device_id_param: str):
    """Registra un device"""
    try:
        await device_hub.register_device(device_id_param, {"platform": "android"})
        logger.info(f"[DEVICE] Registrato: {device_id_param}")
        return {
            "status": "registered",
            "device_id": device_id_param
        }
    except Exception as e:
        logger.error(f"[DEVICE] Registration error: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/api/device/list")
async def list_devices_endpoint():
    """Elenca i device connessi"""
    try:
        devices = device_hub.list_devices()
        return {
            "status": "ok",
            "count": len(devices),
            "devices": devices
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ===== PHONE COMMANDS =====
@app.post("/api/device/call")
async def api_call_phone(data: PhoneCall):
    """Chiama un numero di telefono"""
    try:
        if not device_hub.is_device_connected(device_id):
            return {"status": "error", "message": "❌ Device non connesso"}
        
        logger.info(f"[CALL] Calling {data.phone} (Contact: {data.contact_name})")
        
        await device_hub.send_command(device_id, {
            "type": "command",
            "action": "call_start",
            "id": f"call_{__import__('time').time()}",
            "data": {
                "phone": data.phone,
                "contact_name": data.contact_name
            }
        })
        
        return {
            "status": "ok",
            "message": f"📞 Sto chiamando {data.contact_name or data.phone}..."
        }
    except Exception as e:
        logger.error(f"[CALL] Error: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/api/device/call/end")
async def end_call():
    """Termina una chiamata"""
    try:
        if not device_hub.is_device_connected(device_id):
            return {"status": "error", "message": "❌ Device non connesso"}
        
        logger.info("[CALL] Ending call")
        
        await device_hub.send_command(device_id, {
            "type": "command",
            "action": "call_end",
            "id": f"call_{__import__('time').time()}",
            "data": {}
        })
        
        return {"status": "ok", "message": "📞 Chiamata terminata"}
    except Exception as e:
        logger.error(f"[CALL] Error: {e}")
        return {"status": "error", "message": str(e)}

# ===== WHATSAPP COMMANDS =====
@app.post("/api/device/whatsapp/send")
async def api_whatsapp_send(data: WhatsAppMessage):
    """Invia un messaggio WhatsApp"""
    try:
        if not device_hub.is_device_connected(device_id):
            return {"status": "error", "message": "❌ Device non connesso"}
        
        logger.info(f"[WHATSAPP] Sending to {data.phone}: {data.message}")
        
        await device_hub.send_command(device_id, {
            "type": "command",
            "action": "whatsapp_send",
            "id": f"whats_{__import__('time').time()}",
            "data": {
                "phone": data.phone,
                "message": data.message,
                "contact_name": data.contact_name
            }
        })
        
        return {
            "status": "ok",
            "message": f"💬 Inviando messaggio a {data.contact_name or data.phone}..."
        }
    except Exception as e:
        logger.error(f"[WHATSAPP] Error: {e}")
        return {"status": "error", "message": str(e)}

# ===== NOTIFICATIONS =====
@app.get("/api/device/notifications")
async def api_read_notifications():
    """Leggi le notifiche dal device"""
    try:
        if not device_hub.is_device_connected(device_id):
            return {"status": "error", "message": "❌ Device non connesso"}
        
        logger.info("[NOTIFICATIONS] Reading notifications")
        
        result = await device_hub.send_command(device_id, {
            "type": "command",
            "action": "notifications_read",
            "id": f"notif_{__import__('time').time()}",
            "data": {}
        })
        
        return {
            "status": "ok",
            "notifications": result
        }
    except Exception as e:
        logger.error(f"[NOTIFICATIONS] Error: {e}")
        return {"status": "error", "message": str(e)}

# ===== TEXT COMMANDS (da Web) =====
@app.post("/api/command/text")
async def text_command_endpoint(data: TextCommand):
    """Processa un comando testuale"""
    try:
        cmd_device_id = data.device_id or device_id
        
        if not device_hub.is_device_connected(cmd_device_id):
            devices = device_hub.list_devices()
            if not devices:
                return {"status": "error", "message": "❌ Nessun device connesso"}
            cmd_device_id = devices[0]
        
        logger.info(f"[TEXT] Processing: {data.message}")
        
        result = await jarvis.process_command(data.message, cmd_device_id)
        return result
    except Exception as e:
        logger.error(f"[TEXT] Error: {e}")
        return {"status": "error", "response": str(e)}

# ===== WEBSOCKET FOR DEVICE REGISTRATION =====
@app.websocket("/ws/jarvis")
async def websocket_jarvis_device(websocket: WebSocket):
    """WebSocket per registrazione device e comandi in tempo reale"""
    current_device_id = None
    
    try:
        await websocket.accept()
        logger.info("[WS] Client connesso")
        
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            msg_type = msg.get("type", "")
            
            # ===== REGISTRATION =====
            if msg_type == "register":
                current_device_id = msg.get("device_id", "unknown")
                await device_hub.register_device(current_device_id, {
                    "platform": "android",
                    "ws": websocket
                })
                logger.info(f"[WS] Device registrato: {current_device_id}")
                await websocket.send_json({
                    "type": "status",
                    "message": "✅ Registrato",
                    "device_id": current_device_id
                })
            
            # ===== PING/PONG =====
            elif msg_type == "ping":
                await device_hub.update_heartbeat(current_device_id)
                await websocket.send_json({"type": "pong"})
            
            # ===== RESPONSE =====
            elif msg_type == "response":
                status = msg.get("status", "")
                logger.info(f"[WS] Device response: {status}")
            
            # ===== COMMAND =====
            elif msg_type == "command":
                action = msg.get("action", "")
                logger.info(f"[WS] Device command: {action}")
    
    except WebSocketDisconnect:
        if current_device_id:
            logger.info(f"[WS] Device disconnected: {current_device_id}")
            if current_device_id in device_hub.connected_devices:
                device_hub.connected_devices[current_device_id]["connected"] = False
    
    except Exception as e:
        logger.error(f"[WS] Error: {e}")

# ===== WEBSOCKET FOR WEB CHAT =====
@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket per chat testuale con Jarvis (da interfaccia web)"""
    try:
        await websocket.accept()
        logger.info("[CHAT] Web client connesso")
        
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "")
            
            if msg_type == "message":
                user_input = data.get("message", "").strip()
                if not user_input:
                    continue
                
                logger.info(f"[CHAT] Input: {user_input}")
                await websocket.send_json({"status": "processing"})
                
                try:
                    devices = device_hub.list_devices()
                    cmd_device_id = devices[0] if devices else device_id
                    
                    response = await jarvis.process_command(user_input, cmd_device_id)
                    await websocket.send_json({
                        "status": "ok",
                        "response": response.get("response", str(response))
                    })
                    logger.info(f"[CHAT] Response: {response}")
                except Exception as e:
                    logger.error(f"[CHAT] Error: {e}")
                    await websocket.send_json({
                        "status": "error",
                        "message": str(e)
                    })
            
            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})
    
    except WebSocketDisconnect:
        logger.info("[CHAT] Web client disconnesso")
    except Exception as e:
        logger.error(f"[CHAT] Error: {e}")

# ===== SSL CONTEXT (HTTPS FORZATO) =====
def create_ssl_context():
    """Crea SSL context con certificati Tailscale"""
    # ===== PERCORSI CERTIFICATI =====
    paths_to_try = [
        # Tailscale Linux/WSL
        (Path("/var/lib/tailscale/certs"), "fullchain.pem", "privkey.pem"),
        # Tailscale Windows
        (Path("C:/Program Files/Tailscale/certs"), "fullchain.pem", "privkey.pem"),
        # Local certs
        (Path("certs"), "fullchain.pem", "privkey.pem"),
        (Path("certs"), "cert.pem", "key.pem"),
        # Current directory
        (Path("."), "fullchain.pem", "privkey.pem"),
        (Path("."), "cert.pem", "key.pem"),
    ]
    
    # Ricerca certificati
    for cert_dir, cert_file, key_file in paths_to_try:
        cert_path = cert_dir / cert_file
        key_path = cert_dir / key_file
        
        if cert_path.exists() and key_path.exists():
            logger.info(f"[SSL] ✅ Certificati trovati: {cert_path}")
            
            # Crea SSL context
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ssl_context.load_cert_chain(str(cert_path), str(key_path))
            return ssl_context, str(cert_path), str(key_path)
    
    logger.error("[SSL] ❌ Certificati non trovati!")
    logger.error("[SSL] Cercati in:")
    for cert_dir, _, _ in paths_to_try:
        logger.error(f"  - {cert_dir}")
    return None, None, None

# ===== MAIN =====
async def main():
    """Avvia il server HTTPS"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--voice", action="store_true", help="Abilita riconoscimento vocale")
    parser.add_argument("--http", action="store_true", help="Usa HTTP invece di HTTPS (NON consigliato)")
    args = parser.parse_args()
    
    logger.info("=" * 80)
    logger.info("🤖 JARVIS v2.3.0 - Starting...")
    logger.info("=" * 80)
    
    # Crea SSL context
    ssl_context, cert_path, key_path = create_ssl_context()
    
    if not ssl_context and not args.http:
        logger.error("[SSL] ❌ HTTPS richiesto ma certificati non trovati!")
        logger.error("[SSL] Usa --http per HTTP o posiziona certificati in:")
        logger.error("[SSL]   certs/fullchain.pem")
        logger.error("[SSL]   certs/privkey.pem")
        sys.exit(1)
    
    if args.http:
        logger.warning("[SSL] ⚠️  USANDO HTTP (NON sicuro!) - Usa --http solo per test")
        cert_path = None
        key_path = None
        ssl_context = None
    else:
        logger.info(f"[SSL] ✅ HTTPS FORZATO")
        logger.info(f"[SSL] Certificato: {cert_path}")
        logger.info(f"[SSL] Chiave privata: {key_path}")
    
    logger.info(f"[CONFIG] Device: {device_id}")
    logger.info("[SERVER] Running on https://0.0.0.0:5000")
    logger.info("[INTERFACE] Open: https://nwe-pasqualini.tail3fb552.ts.net:5000/")
    logger.info("[FEATURES] ✅ Weather, Phone Calls, WhatsApp, Notifications")
    logger.info("[WS] ✅ WebSocket enabled for device + chat")
    
    if args.voice:
        logger.info("[VOICE] ✅ Voice recognition enabled")
    else:
        logger.info("[VOICE] ⚠️  Voice recognition disabled")
    
    # Configurazione Uvicorn
    config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=5000,
        log_level="info",
        access_log=False,
        ssl_keyfile=key_path if key_path else None,
        ssl_certfile=cert_path if cert_path else None,
    )
    server = uvicorn.Server(config)
    
    await server.serve()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("[EXIT] 👋 Goodbye!")
        sys.exit(0)
    except Exception as e:
        logger.error(f"[FATAL] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)