import os
import uvicorn
from fastapi import FastAPI, Query
from pydantic import BaseModel
from typing import Optional

# Plugin concreti (rispettano la tua struttura)
from services.device_control import android_adb as device
from services.weather import openweather as weather

app = FastAPI(title="JARVIS Actions API", version="1.0.0")

# ===== Schemi =====
class ToggleSchema(BaseModel):
    state: bool

class VolumeSchema(BaseModel):
    level: int

class SMSchema(BaseModel):
    phone: str
    message: str

class CallSchema(BaseModel):
    phone: str

class ScreenRecordSchema(BaseModel):
    duration_sec: int = 30

# ===== DEVICE =====
@app.get("/api/device/battery")
def get_battery():
    return device.get_battery_status()

@app.post("/api/device/wifi")
def toggle_wifi(payload: ToggleSchema):
    return device.toggle_wifi(payload.state)

@app.post("/api/device/bluetooth")
def toggle_bluetooth(payload: ToggleSchema):
    return device.toggle_bluetooth(payload.state)

@app.post("/api/device/airplane")
def toggle_airplane(payload: ToggleSchema):
    return device.toggle_airplane_mode(payload.state)

@app.post("/api/device/volume")
def set_volume(payload: VolumeSchema):
    return device.set_volume(payload.level)

@app.post("/api/device/flashlight")
def toggle_flashlight(payload: ToggleSchema):
    return device.toggle_flashlight(payload.state)

@app.post("/api/device/screenshot")
def take_screenshot():
    return device.take_screenshot()

@app.post("/api/device/screenrecord")
def record_screen(payload: ScreenRecordSchema):
    return device.record_screen(payload.duration_sec)

@app.get("/api/device/notifications")
def read_notifications():
    return device.get_notifications()

@app.post("/api/device/sms")
def send_sms(payload: SMSchema):
    return device.send_sms(payload.phone, payload.message)

@app.post("/api/device/whatsapp")
def send_whatsapp(payload: SMSchema):
    return device.send_whatsapp(payload.phone, payload.message)

@app.post("/api/device/call")
def make_call(payload: CallSchema):
    return device.make_call(payload.phone)

@app.post("/api/device/call/end")
def end_call():
    return device.end_call()

@app.post("/api/device/camera/shot")
def camera_shot():
    return device.camera_shot()

# ===== WEATHER =====
@app.get("/api/weather/current")
def weather_current(
    city: Optional[str] = Query(None),
    lat: Optional[float] = Query(None),
    lon: Optional[float] = Query(None),
    units: str = Query("metric")
):
    return weather.current(city=city, lat=lat, lon=lon, units=units)

@app.get("/api/weather/hourly")
def weather_hourly(
    city: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    hours: int = 48,
    units: str = "metric"
):
    return weather.hourly(city=city, lat=lat, lon=lon, hours=hours, units=units)

@app.get("/api/weather/daily")
def weather_daily(
    city: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    days: int = 7,
    units: str = "metric"
):
    return weather.daily(city=city, lat=lat, lon=lon, days=days, units=units)

@app.get("/api/weather/air_quality")
def weather_aqi(lat: float, lon: float):
    return weather.air_quality(lat=lat, lon=lon)

@app.get("/api/weather/alerts")
def weather_alerts(
    city: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None
):
    return weather.alerts(city=city, lat=lat, lon=lon)

if __name__ == "__main__":
    host = os.environ.get("ACTIONS_HOST", "0.0.0.0")
    port = int(os.environ.get("ACTIONS_PORT", "8000"))
    uvicorn.run("services.api_server:app", host=host, port=port, reload=True)
