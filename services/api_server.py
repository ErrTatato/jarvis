import asyncio
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import json
from typing import Optional
from core.jarvis_ai import JarvisAI
from services.device_hub import DeviceHub

logger = logging.getLogger(__name__)

class APIServer:
    def __init__(self, app: FastAPI):
        self.app = app
        self.jarvis = JarvisAI()
        self.device_hub = DeviceHub()
        self.jarvis.set_device_hub(self.device_hub)
        
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup tutti gli endpoint"""
        
        # ===== STATUS & HEALTH =====
        @self.app.get("/api/status")
        async def status():
            """Status della API e device connessi"""
            connected_devices = self.device_hub.list_devices()
            return {
                "status": "running",
                "version": "2.3.0",
                "devices_connected": len(connected_devices),
                "device_list": connected_devices,
                "timestamp": __import__('datetime').datetime.now().isoformat()
            }
        
        @self.app.get("/api/health")
        async def health():
            """Health check"""
            return {
                "status": "ok",
                "timestamp": __import__('datetime').datetime.now().isoformat()
            }
        
        # ===== DEVICE MANAGEMENT =====
        @self.app.get("/api/device/register")
        async def register_device(device_id: str):
            """Registra un device"""
            try:
                await self.device_hub.register_device(device_id, {"platform": "android"})
                return {
                    "status": "registered",
                    "device_id": device_id
                }
            except Exception as e:
                logger.error(f"Register error: {e}")
                return JSONResponse(
                    {"status": "error", "message": str(e)},
                    status_code=500
                )
        
        @self.app.get("/api/device/list")
        async def list_devices():
            """Elenca i device connessi"""
            devices = self.device_hub.list_devices()
            return {
                "status": "ok",
                "count": len(devices),
                "devices": devices
            }
        
        # ===== COMANDI =====
        @self.app.post("/api/command")
        async def send_command(device_id: str, action: str, data: dict = None):
            """Invia un comando a un device"""
            try:
                if not self.device_hub.is_device_connected(device_id):
                    return JSONResponse(
                        {"status": "error", "message": "Device not connected"},
                        status_code=400
                    )
                
                await self.device_hub.send_command(device_id, {
                    "type": "command",
                    "action": action,
                    "data": data or {}
                })
                
                return {
                    "status": "sent",
                    "device_id": device_id,
                    "action": action
                }
            except Exception as e:
                logger.error(f"Command error: {e}")
                return JSONResponse(
                    {"status": "error", "message": str(e)},
                    status_code=500
                )
        
        # ===== METEO =====
        @self.app.get("/api/weather/{city}")
        async def get_weather(city: str):
            """Ottiene il meteo per una città"""
            try:
                result = await self.jarvis._handle_weather(f"meteo {city}")
                return result
            except Exception as e:
                logger.error(f"Weather error: {e}")
                return JSONResponse(
                    {"status": "error", "message": str(e)},
                    status_code=500
                )
        
        # ===== COMANDI VOCALI =====
        @self.app.post("/api/command/text")
        async def text_command(command: str, device_id: str = None):
            """Processa un comando testuale"""
            try:
                if not device_id:
                    devices = self.device_hub.list_devices()
                    if devices:
                        device_id = devices[0]
                    else:
                        return JSONResponse(
                            {"status": "error", "message": "No device connected"},
                            status_code=400
                        )
                
                result = await self.jarvis.process_command(command, device_id)
                return result
            except Exception as e:
                logger.error(f"Command error: {e}")
                return JSONResponse(
                    {"status": "error", "message": str(e)},
                    status_code=500
                )
        
        # ===== WEBSOCKET =====
        @self.app.websocket("/ws/jarvis")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket per comunicazione real-time con device"""
            device_id = None
            try:
                await websocket.accept()
                
                initial_msg = await websocket.receive_text()
                initial_data = json.loads(initial_msg)
                
                if initial_data.get("type") == "register":
                    device_id = initial_data.get("device_id", "unknown")
                    await self.device_hub.register_device(device_id, {
                        "platform": "android",
                        "ws": websocket
                    })
                    logger.info(f"[WS] Device registered: {device_id}")
                    await websocket.send_json({
                        "type": "status",
                        "message": "✅ Registered",
                        "device_id": device_id
                    })
                
                while True:
                    data = await websocket.receive_text()
                    msg = json.loads(data)
                    msg_type = msg.get("type")
                    
                    if msg_type == "ping":
                        await self.device_hub.update_heartbeat(device_id)
                        await websocket.send_json({"type": "pong"})
                    
                    elif msg_type == "response":
                        status = msg.get("status")
                        logger.info(f"[WS] Device response: {status}")
                    
                    elif msg_type == "command":
                        logger.warning(f"[WS] Device sent command (unexpected)")
            
            except WebSocketDisconnect:
                if device_id:
                    logger.info(f"[WS] Device disconnected: {device_id}")
                    if device_id in self.device_hub.connected_devices:
                        self.device_hub.connected_devices[device_id]["connected"] = False
            
            except Exception as e:
                logger.error(f"[WS] Error: {e}")
                if device_id:
                    if device_id in self.device_hub.connected_devices:
                        self.device_hub.connected_devices[device_id]["connected"] = False