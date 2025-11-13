import asyncio
import json
import logging
import ssl
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from contextlib import asynccontextmanager
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("JARVIS-DeviceBridge")

# ============== DEVICE MANAGER ==============

class DeviceManager:
    """Manages connected Android devices"""
    
    def __init__(self):
        self.connected_devices: Dict[str, Dict[str, Any]] = {}
    
    def register(self, device_id: str, websocket: WebSocket, metadata: Dict = None):
        """Register a new device"""
        self.connected_devices[device_id] = {
            "websocket": websocket,
            "connected_at": datetime.now(),
            "last_heartbeat": datetime.now(),
            "metadata": metadata or {},
            "status": "online"
        }
        logger.info(f"✅ Device registered: {device_id}")
    
    def unregister(self, device_id: str):
        """Unregister a device"""
        if device_id in self.connected_devices:
            del self.connected_devices[device_id]
            logger.info(f"❌ Device unregistered: {device_id}")
    
    def get_device(self, device_id: str) -> Optional[Dict]:
        """Get device info"""
        return self.connected_devices.get(device_id)
    
    def is_connected(self, device_id: str) -> bool:
        """Check if device is connected"""
        return device_id in self.connected_devices
    
    def get_websocket(self, device_id: str) -> Optional[WebSocket]:
        """Get device WebSocket"""
        device = self.get_device(device_id)
        return device["websocket"] if device else None
    
    async def send_command(self, device_id: str, command: Dict[str, Any]) -> bool:
        """Send command to device"""
        ws = self.get_websocket(device_id)
        if not ws:
            logger.error(f"❌ Device not connected: {device_id}")
            return False
        
        try:
            await ws.send_json(command)
            logger.info(f"📤 Command sent to {device_id}: {command.get('action')}")
            return True
        except Exception as e:
            logger.error(f"❌ Send command error: {e}")
            return False
    
    def list_devices(self) -> list:
        """List all connected devices"""
        return list(self.connected_devices.keys())

# ============== INITIALIZE ==============

device_manager = DeviceManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    logger.info("🚀 JARVIS Device Bridge started")
    yield
    logger.info("🛑 JARVIS Device Bridge stopped")

app = FastAPI(title="JARVIS Device Bridge", lifespan=lifespan)

# ============== WEBSOCKET ENDPOINT ==============

@app.websocket("/ws/device")
async def websocket_device_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for Android devices
    Handles device registration, heartbeats, commands, and responses
    """
    await websocket.accept()
    device_id = None
    
    try:
        logger.info("🔗 New WebSocket connection")
        
        while True:
            # Wait for message with 35-second timeout (> 30s heartbeat)
            data = await asyncio.wait_for(
                websocket.receive_text(),
                timeout=35.0
            )
            
            message = json.loads(data)
            message_type = message.get("type", "unknown")
            
            logger.debug(f"📨 Received: {message_type}")
            
            # ========== DEVICE REGISTRATION ==========
            if not device_id:
                device_id = message.get("device_id")
                if device_id:
                    metadata = {
                        "os": "Android",
                        "app_version": message.get("app_version", "unknown"),
                        "device_name": message.get("device_name", "unknown")
                    }
                    device_manager.register(device_id, websocket, metadata)
                    logger.info(f"✅ DEVICE BRIDGE CONNECTED! [{device_id}]")
            
            # ========== HEARTBEAT ==========
            if message_type == "heartbeat":
                response = {
                    "type": "heartbeat_ack",
                    "status": "ok",
                    "timestamp": message.get("timestamp"),
                    "server_time": datetime.now().isoformat()
                }
                await websocket.send_json(response)
                device_manager.connected_devices[device_id]["last_heartbeat"] = datetime.now()
                logger.debug(f"💓 Heartbeat ACK sent to {device_id}")
            
            # ========== COMMAND RESPONSE ==========
            elif message_type == "command_response":
                action = message.get("action", "unknown")
                success = message.get("success", False)
                response_msg = message.get("message", "")
                
                status_icon = "✅" if success else "❌"
                logger.info(f"📤 Device response: {action} {status_icon}")
                logger.debug(f"   Message: {response_msg}")
            
            # ========== DEVICE STATUS ==========
            elif message_type == "device_status":
                battery = message.get("battery", 0)
                signal = message.get("signal_strength", 0)
                
                logger.info(f"📊 Device status: Battery={battery}%, Signal={signal}%")
                device_manager.connected_devices[device_id]["metadata"]["battery"] = battery
                device_manager.connected_devices[device_id]["metadata"]["signal"] = signal
            
            # ========== ERROR ==========
            elif message_type == "error":
                error_msg = message.get("message", "Unknown error")
                logger.error(f"❌ Device error: {error_msg}")
            
            # ========== UNKNOWN ==========
            else:
                logger.warning(f"⚠️ Unknown message type: {message_type}")
    
    except asyncio.TimeoutError:
        logger.warning(f"⏱️ Timeout: Device {device_id} didn't send heartbeat")
    
    except WebSocketDisconnect:
        logger.info(f"🔌 Device {device_id} disconnected (client)")
    
    except Exception as e:
        logger.error(f"❌ WebSocket error: {e}", exc_info=True)
    
    finally:
        if device_id:
            device_manager.unregister(device_id)
            logger.info(f"❌ Device {device_id} disconnected")
        
        try:
            await websocket.close()
        except:
            pass

# ============== REST ENDPOINTS ==============

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "JARVIS Device Bridge",
        "connected_devices": device_manager.list_devices(),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/devices")
async def get_devices():
    """Get list of connected devices"""
    devices = []
    for device_id, info in device_manager.connected_devices.items():
        devices.append({
            "device_id": device_id,
            "status": info["status"],
            "connected_at": info["connected_at"].isoformat(),
            "last_heartbeat": info["last_heartbeat"].isoformat(),
            "metadata": info["metadata"]
        })
    return {"devices": devices, "count": len(devices)}

@app.get("/devices/{device_id}")
async def get_device(device_id: str):
    """Get specific device info"""
    device = device_manager.get_device(device_id)
    if not device:
        return {"error": f"Device {device_id} not found"}
    
    return {
        "device_id": device_id,
        "status": device["status"],
        "connected_at": device["connected_at"].isoformat(),
        "last_heartbeat": device["last_heartbeat"].isoformat(),
        "metadata": device["metadata"]
    }

@app.post("/devices/{device_id}/command")
async def send_command(device_id: str, command: Dict[str, Any]):
    """Send command to device via HTTP"""
    if not device_manager.is_connected(device_id):
        return {"error": f"Device {device_id} not connected"}
    
    success = await device_manager.send_command(device_id, command)
    return {"success": success, "device_id": device_id}

# ============== STARTUP ==============

if __name__ == "__main__":
    # Setup SSL context
    ssl_keyfile = "key.pem"
    ssl_certfile = "cert.pem"
    
    # Check if SSL files exist
    import os
    ssl_context = None
    if os.path.exists(ssl_keyfile) and os.path.exists(ssl_certfile):
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(ssl_certfile, ssl_keyfile)
        logger.info("🔒 SSL/TLS enabled")
    else:
        logger.warning("⚠️ SSL certificates not found. Running without SSL.")
    
    # Start server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=5000,
        ssl_keyfile=ssl_keyfile if ssl_context else None,
        ssl_certfile=ssl_certfile if ssl_context else None,
        log_level="info"
    )