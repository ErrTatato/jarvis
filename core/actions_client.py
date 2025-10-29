import os
import httpx

ACTIONS_BASE = os.environ.get("ACTIONS_BASE_URL", "http://localhost:8000")

async def _post(path: str, json=None, timeout=15):
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(f"{ACTIONS_BASE}{path}", json=json or {})
        r.raise_for_status()
        return r.json()

async def _get(path: str, params=None, timeout=15):
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.get(f"{ACTIONS_BASE}{path}", params=params or {})
        r.raise_for_status()
        return r.json()

# DEVICE
async def device_battery(): return await _get("/api/device/battery")
async def device_wifi(state: bool): return await _post("/api/device/wifi", {"state": state})
async def device_bluetooth(state: bool): return await _post("/api/device/bluetooth", {"state": state})
async def device_airplane(state: bool): return await _post("/api/device/airplane", {"state": state})
async def device_volume(level: int): return await _post("/api/device/volume", {"level": level})
async def device_flashlight(state: bool): return await _post("/api/device/flashlight", {"state": state})
async def device_screenshot(): return await _post("/api/device/screenshot")
async def device_screenrecord(duration: int): return await _post("/api/device/screenrecord", {"duration_sec": duration})
async def device_notifications(): return await _get("/api/device/notifications")
async def device_sms(phone: str, message: str): return await _post("/api/device/sms", {"phone": phone, "message": message})
async def device_whatsapp(phone: str, message: str): return await _post("/api/device/whatsapp", {"phone": phone, "message": message})
async def device_call(phone: str): return await _post("/api/device/call", {"phone": phone})
async def device_call_end(): return await _post("/api/device/call/end")
async def device_camera_shot(): return await _post("/api/device/camera/shot")

# WEATHER
async def wx_current(city=None, lat=None, lon=None, units="metric"):
    return await _get("/api/weather/current", {"city": city, "lat": lat, "lon": lon, "units": units})

async def wx_hourly(city=None, lat=None, lon=None, hours=48, units="metric"):
    return await _get("/api/weather/hourly", {"city": city, "lat": lat, "lon": lon, "hours": hours, "units": units})

async def wx_daily(city=None, lat=None, lon=None, days=7, units="metric"):
    return await _get("/api/weather/daily", {"city": city, "lat": lat, "lon": lon, "days": days, "units": units})

async def wx_aqi(lat, lon):
    return await _get("/api/weather/air_quality", {"lat": lat, "lon": lon})

async def wx_alerts(city=None, lat=None, lon=None):
    return await _get("/api/weather/alerts", {"city": city, "lat": lat, "lon": lon})
