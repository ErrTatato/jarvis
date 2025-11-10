# services/api_server.py
import os
import ssl
import logging
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="JARVIS API", version="2.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== Pydantic Models =====
class BaseCmd(BaseModel):
    device_id: str

class ToggleCmd(BaseCmd):
    state: bool

class VolumeCmd(BaseCmd):
    level: int

class PhoneMsgCmd(BaseCmd):
    phone: str
    message: str

class PhoneCmd(BaseCmd):
    phone: str

class ScreenRecCmd(BaseCmd):
    duration_sec: int = 30

class WhatsSendCmd(BaseCmd):
    phone: str
    message: str

class WhatsReplyCmd(BaseCmd):
    thread_hint: str | None = None
    message: str

# ===== Device Registration & WebSocket =====
@app.post("/api/device/register")
async def register_device_post(device_id: str):
    from services.device_hub import register_device
    register_device(device_id)
    return {"status": "ok", "device_id": device_id}

@app.get("/api/device/register")
async def register_device_get(device_id: str = Query(...)):
    from services.device_hub import register_device
    register_device(device_id)
    return {"status": "ok", "device_id": device_id}

@app.post("/api/device/heartbeat")
async def device_heartbeat(device_id: str):
    from services.device_hub import register_device
    register_device(device_id)
    return {"status": "ok"}

@app.get("/api/info/connected_devices")
async def connected():
    from services.device_hub import list_devices
    return {"devices": list_devices()}

@app.websocket("/ws/device/{device_id}")
async def websocket_device(websocket: WebSocket, device_id: str):
    """WebSocket endpoint per device connesso"""
    from services.device_hub import ws_handler
    try:
        await ws_handler(websocket, device_id)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"[WS] Error: {e}")

# ===== Helper funzione send_to_device =====
async def send_to_device(device_id: str, action: str, data: dict):
    from services.device_hub import send_command, is_device_connected
    if not is_device_connected(device_id):
        return {"status": "error", "message": "device_not_connected", "data": {}}
    rep = await send_command(device_id, {"type": "command", "action": action, "data": data})
    return {
        "status": "success" if rep.get("ok") else "error",
        "data": rep.get("data", {}),
        "message": rep.get("error")
    }

# ===== Device Commands =====
@app.get("/api/device/battery")
async def get_battery(device_id: str):
    return await send_to_device(device_id, "battery_status", {})

@app.post("/api/device/wifi")
async def toggle_wifi(cmd: ToggleCmd):
    return await send_to_device(cmd.device_id, "wifi_toggle", {"state": cmd.state})

@app.post("/api/device/bluetooth")
async def toggle_bluetooth(cmd: ToggleCmd):
    return await send_to_device(cmd.device_id, "bt_toggle", {"state": cmd.state})

@app.post("/api/device/airplane")
async def toggle_airplane(cmd: ToggleCmd):
    return await send_to_device(cmd.device_id, "airplane_toggle", {"state": cmd.state})

@app.post("/api/device/volume")
async def set_volume(cmd: VolumeCmd):
    return await send_to_device(cmd.device_id, "volume_set", {"level": cmd.level})

@app.post("/api/device/flashlight")
async def toggle_flashlight(cmd: ToggleCmd):
    return await send_to_device(cmd.device_id, "flashlight", {"state": cmd.state})

@app.post("/api/device/screenshot")
async def take_screenshot(cmd: BaseCmd):
    return await send_to_device(cmd.device_id, "screenshot", {})

@app.post("/api/device/screenrecord")
async def record_screen(cmd: ScreenRecCmd):
    return await send_to_device(cmd.device_id, "screenrecord", {"duration_sec": cmd.duration_sec})

@app.get("/api/device/notifications")
async def read_notifications(device_id: str):
    return await send_to_device(device_id, "notifications_read", {})

@app.post("/api/device/sms")
async def send_sms(cmd: PhoneMsgCmd):
    return await send_to_device(cmd.device_id, "sms_send", {"phone": cmd.phone, "message": cmd.message})

@app.post("/api/device/call/start")
async def call_start(cmd: PhoneCmd):
    return await send_to_device(cmd.device_id, "call_start", {"phone": cmd.phone})

@app.post("/api/device/call/end")
async def call_end(cmd: BaseCmd):
    return await send_to_device(cmd.device_id, "call_end", {})

@app.post("/api/whatsapp/send")
async def whatsapp_send(cmd: WhatsSendCmd):
    return await send_to_device(cmd.device_id, "whatsapp_send", {"phone": cmd.phone, "message": cmd.message})

@app.post("/api/whatsapp/reply")
async def whatsapp_reply(cmd: WhatsReplyCmd):
    return await send_to_device(cmd.device_id, "whatsapp_reply", {"thread_hint": cmd.thread_hint, "message": cmd.message})

# ===== Weather API (se disponibile) =====
def to_float(x):
    try:
        return float(x) if x not in (None, "") else None
    except:
        return None

try:
    from services.weather import weather_api as weather

    @app.get("/api/weather/current")
    async def weather_current(city: str = None, lat: str = None, lon: str = None, units: str = "metric"):
        return weather.current(city=city, lat=to_float(lat), lon=to_float(lon), units=units)

    @app.get("/api/weather/hourly")
    async def weather_hourly(city: str = None, lat: str = None, lon: str = None, hours: int = 48, units: str = "metric"):
        return weather.hourly(city=city, lat=to_float(lat), lon=to_float(lon), hours=hours, units=units)

    @app.get("/api/weather/daily")
    async def weather_daily(city: str = None, lat: str = None, lon: str = None, days: int = 7, units: str = "metric"):
        return weather.daily(city=city, lat=to_float(lat), lon=to_float(lon), days=days, units=units)

    @app.get("/api/weather/air_quality")
    async def weather_aqi(lat: str, lon: str):
        return weather.air_quality(lat=to_float(lat), lon=to_float(lon))

    @app.get("/api/weather/alerts")
    async def weather_alerts(city: str = None, lat: str = None, lon: str = None):
        return weather.alerts(city=city, lat=to_float(lat), lon=to_float(lon))
except Exception as e:
    logger.warning(f"[WEATHER] Not available: {e}")

@app.get("/")
async def root():
    return {"status": "running", "version": "2.3.0"}

if __name__ == "__main__":
    host = os.environ.get("ACTIONS_HOST", "0.0.0.0")
    port = int(os.environ.get("ACTIONS_PORT", "8000"))
    cert = "certs/cert.pem"
    key = "certs/key.pem"
    
    if os.path.exists(cert) and os.path.exists(key):
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(cert, key)
        logger.info(f"[SSL] ✅ HTTPS enabled on {host}:{port}")
        uvicorn.run("services.api_server:app", host=host, port=port, ssl_context=ctx, reload=False, log_level="info")
    else:
        logger.error(f"[SSL] ❌ Certificati non trovati: {cert}, {key}")
        logger.info(f"[HTTP] Avviando in HTTP su {host}:{port}")
        uvicorn.run("services.api_server:app", host=host, port=port, reload=False, log_level="info")
