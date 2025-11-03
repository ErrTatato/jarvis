# core/actions_client.py
import os
import httpx
from typing import Any, Dict, Optional

ACTIONS_BASE = os.environ.get("ACTIONS_BASE_URL", "https://YOUR-TAILSCALE-HOST:8000")
PRIMARY_DEVICE_ID = os.environ.get("JARVIS_PRIMARY_DEVICE_ID", "mi13pro")
TIMEOUT = float(os.environ.get("ACTIONS_TIMEOUT", "12"))
VERIFY = os.environ.get("ACTIONS_SSL_VERIFY", "true").lower() != "false"

def _url(p: str) -> str:
    return f"{ACTIONS_BASE.rstrip('/')}{p}"

async def _get(path: str, params: Optional[Dict[str, Any]] = None):
    async with httpx.AsyncClient(timeout=TIMEOUT, verify=VERIFY) as c:
        r = await c.get(_url(path), params=params)
        return r.json()

async def _post(path: str, json: Optional[Dict[str, Any]] = None):
    async with httpx.AsyncClient(timeout=TIMEOUT, verify=VERIFY) as c:
        r = await c.post(_url(path), json=json or {})
        return r.json()

# Device
async def device_battery(device_id: str = PRIMARY_DEVICE_ID):
    return await _get("/api/device/battery", {"device_id": device_id})

async def device_wifi(device_id: str, state: bool):
    return await _post("/api/device/wifi", {"device_id": device_id, "state": state})

async def device_bluetooth(device_id: str, state: bool):
    return await _post("/api/device/bluetooth", {"device_id": device_id, "state": state})

async def device_airplane(device_id: str, state: bool):
    return await _post("/api/device/airplane", {"device_id": device_id, "state": state})

async def device_volume(device_id: str, level: int):
    return await _post("/api/device/volume", {"device_id": device_id, "level": level})

async def device_flashlight(device_id: str, state: bool):
    return await _post("/api/device/flashlight", {"device_id": device_id, "state": state})

async def device_screenshot(device_id: str):
    return await _post("/api/device/screenshot", {"device_id": device_id})

async def device_screenrecord(device_id: str, duration_sec: int):
    return await _post("/api/device/screenrecord", {"device_id": device_id, "duration_sec": duration_sec})

async def device_notifications(device_id: str):
    return await _get("/api/device/notifications", {"device_id": device_id})

async def device_sms(device_id: str, phone: str, message: str):
    return await _post("/api/device/sms", {"device_id": device_id, "phone": phone, "message": message})

async def device_whatsapp(device_id: str, phone: str, message: str):
    return await _post("/api/whatsapp/send", {"device_id": device_id, "phone": phone, "message": message})

async def device_call(device_id: str, phone: str):
    return await _post("/api/device/call/start", {"device_id": device_id, "phone": phone})

async def device_call_end(device_id: str):
    return await _post("/api/device/call/end", {"device_id": device_id})

async def device_camera_shot(device_id: str):
    return await _post("/api/device/camera/shot", {"device_id": device_id})

# Weather
async def wx_current(city: str = None, lat: float = None, lon: float = None, units: str = "metric"):
    return await _get("/api/weather/current", {"city": city, "lat": lat, "lon": lon, "units": units})

async def wx_hourly(city: str = None, hours: int = 12, units: str = "metric"):
    return await _get("/api/weather/hourly", {"city": city, "hours": hours, "units": units})

async def wx_daily(city: str = None, days: int = 7, units: str = "metric"):
    return await _get("/api/weather/daily", {"city": city, "days": days, "units": units})

async def wx_aqi(lat: float, lon: float):
    return await _get("/api/weather/air_quality", {"lat": lat, "lon": lon})

async def wx_alerts(city: str = None, lat: float = None, lon: float = None):
    return await _get("/api/weather/alerts", {"city": city, "lat": lat, "lon": lon})
