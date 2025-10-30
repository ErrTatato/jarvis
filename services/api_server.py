import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Importa il router WebSocket dal device_hub
from services.device_hub import router as hub_router, send_command
from services.weather import weather_api as weather

app = FastAPI(title="JARVIS Actions API", version="2.1.0")

# Abilita CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Includi il router WebSocket (è IMPORTANTE!)
app.include_router(hub_router)

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

async def _send(device_id: str, action: str, data: dict, timeout: float = 12.0):
    payload = {"type": "command", "action": action, "data": data}
    rep = await send_command(device_id, payload, timeout=timeout)
    ok = rep.get("ok", False)
    return {"status": "success" if ok else "error", "data": rep.get("data"), "message": rep.get("error")}

@app.get("/api/device/battery")
async def get_battery(device_id: str): 
    return await _send(device_id, "battery_status", {})

@app.post("/api/device/wifi")
async def toggle_wifi(cmd: ToggleCmd): 
    return await _send(cmd.device_id, "wifi_toggle", {"state": cmd.state})

@app.post("/api/device/bluetooth")
async def toggle_bluetooth(cmd: ToggleCmd): 
    return await _send(cmd.device_id, "bt_toggle", {"state": cmd.state})

@app.post("/api/device/airplane")
async def toggle_airplane(cmd: ToggleCmd): 
    return await _send(cmd.device_id, "airplane_toggle", {"state": cmd.state})

@app.post("/api/device/volume")
async def set_volume(cmd: VolumeCmd): 
    return await _send(cmd.device_id, "volume_set", {"level": cmd.level})

@app.post("/api/device/flashlight")
async def toggle_flashlight(cmd: ToggleCmd): 
    return await _send(cmd.device_id, "flashlight", {"state": cmd.state})

@app.post("/api/device/screenshot")
async def take_screenshot(cmd: BaseCmd): 
    return await _send(cmd.device_id, "screenshot", {})

@app.post("/api/device/screenrecord")
async def record_screen(cmd: ScreenRecCmd): 
    return await _send(cmd.device_id, "screenrecord", {"duration_sec": cmd.duration_sec})

@app.get("/api/device/notifications")
async def read_notifications(device_id: str): 
    return await _send(device_id, "notifications_read", {})

@app.post("/api/device/sms")
async def send_sms(cmd: PhoneMsgCmd): 
    return await _send(cmd.device_id, "sms_send", {"phone": cmd.phone, "message": cmd.message})

@app.post("/api/device/whatsapp")
async def send_whatsapp(cmd: PhoneMsgCmd): 
    return await _send(cmd.device_id, "whatsapp_send", {"phone": cmd.phone, "message": cmd.message})

@app.post("/api/device/call")
async def make_call(cmd: PhoneCmd): 
    return await _send(cmd.device_id, "call_start", {"phone": cmd.phone})

@app.post("/api/device/call/end")
async def end_call(cmd: BaseCmd): 
    return await _send(cmd.device_id, "call_end", {})

@app.post("/api/device/camera/shot")
async def camera_shot(cmd: BaseCmd): 
    return await _send(cmd.device_id, "camera_shot", {})

def _to_float(x):
    try: return float(x) if x not in (None,"") else None
    except: return None

@app.get("/api/weather/current")
async def weather_current(city: str|None=None, lat: str|None=None, lon: str|None=None, units: str="metric"):
    return weather.current(city=city, lat=_to_float(lat), lon=_to_float(lon), units=units)

@app.get("/api/weather/hourly")
async def weather_hourly(city: str|None=None, lat: str|None=None, lon: str|None=None, hours: int=48, units: str="metric"):
    return weather.hourly(city=city, lat=_to_float(lat), lon=_to_float(lon), hours=hours, units=units)

@app.get("/api/weather/daily")
async def weather_daily(city: str|None=None, lat: str|None=None, lon: str|None=None, days: int=7, units: str="metric"):
    return weather.daily(city=city, lat=_to_float(lat), lon=_to_float(lon), days=days, units=units)

@app.get("/api/weather/air_quality")
async def weather_aqi(lat: str, lon: str):
    return weather.air_quality(lat=_to_float(lat), lon=_to_float(lon))

@app.get("/api/weather/alerts")
async def weather_alerts(city: str|None=None, lat: str|None=None, lon: str|None=None):
    return weather.alerts(city=city, lat=_to_float(lat), lon=_to_float(lon))

@app.get("/api/info/primary_device_id")
async def get_primary_device_id():
    return {"device_id": os.environ.get("JARVIS_PRIMARY_DEVICE_ID","")}

@app.get("/api/info/connected_devices")
async def get_connected_devices():
    from services.device_hub import list_devices
    return {"devices": list_devices()}

@app.get("/api/info/connected_devices")
async def get_connected_devices():
    from services.device_hub import list_devices
    devices = list_devices()
    return {"devices": devices}
@app.post("/api/device/register")
async def register_device(device_id: str):
    """Registra il device nel hub"""
    from services.device_hub import devices_registry
    devices_registry.add(device_id)
    return {"status": "registered", "device_id": device_id}

@app.get("/api/info/connected_devices")
async def get_connected_devices():
    from services.device_hub import list_devices
    devices = list_devices()
    return {"devices": devices}


if __name__ == "__main__":
    host = os.environ.get("ACTIONS_HOST", "0.0.0.0")
    port = int(os.environ.get("ACTIONS_PORT", "8000"))
    uvicorn.run("services.api_server:app", host=host, port=port, reload=True)
