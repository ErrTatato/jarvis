# services/device_hub.py - DEVICE MANAGEMENT PER ANDROID
import asyncio
import logging
from typing import Dict, List, Optional, Any
import aiohttp

logger = logging.getLogger(__name__)

# Simulazione device connessi (in produzione: usare database)
CONNECTED_DEVICES: Dict[str, Dict[str, Any]] = {}

# Timeout per le risposte dai device
DEVICE_TIMEOUT = 10

class DeviceHub:
    """Gestisce la comunicazione con i device Android"""
    
    @staticmethod
    async def register_device(device_id: str, device_info: Dict) -> bool:
        """Registra un device come connesso"""
        try:
            CONNECTED_DEVICES[device_id] = {
                "id": device_id,
                "connected": True,
                "last_heartbeat": __import__('time').time(),
                **device_info
            }
            logger.info(f"[DEVICE] ✅ Registered: {device_id}")
            return True
        except Exception as e:
            logger.error(f"[DEVICE] Error registering {device_id}: {e}")
            return False
    
    @staticmethod
    def is_device_connected(device_id: str) -> bool:
        """Verifica se un device è connesso"""
        if device_id in CONNECTED_DEVICES:
            device = CONNECTED_DEVICES[device_id]
            # Verifica heartbeat (max 30 secondi)
            import time
            if time.time() - device.get("last_heartbeat", 0) < 30:
                return device.get("connected", False)
            else:
                # Device scaduto
                CONNECTED_DEVICES[device_id]["connected"] = False
                return False
        return False
    
    @staticmethod
    def list_devices() -> List[str]:
        """Elenco dei device connessi"""
        return [
            dev_id for dev_id, dev in CONNECTED_DEVICES.items() 
            if DeviceHub.is_device_connected(dev_id)
        ]
    
    @staticmethod
    async def send_command(device_id: str, command: Dict) -> Dict[str, Any]:
        """
        Invia un comando a un device
        
        Args:
            device_id: ID del device
            command: {
                "type": "command",
                "action": "call_start|call_end|whatsapp_send|etc",
                "data": {...}
            }
        
        Returns:
            Risposta dal device
        """
        if not DeviceHub.is_device_connected(device_id):
            return {
                "status": "error",
                "message": f"Device {device_id} non connesso"
            }
        
        try:
            logger.info(f"[DEVICE] Sending to {device_id}: {command.get('action')}")
            
            # Nel tuo caso, i comandi vengono ricevuti via WebSocket
            # Qui dovremmo implementare un sistema di code di messaggi
            # Per ora, simuliamo una risposta positiva
            
            device = CONNECTED_DEVICES[device_id]
            action = command.get("action", "")
            
            if action == "call_start":
                phone = command.get("data", {}).get("phone", "")
                logger.info(f"[CALL] Calling {phone} on {device_id}")
                return {"status": "success", "message": f"Calling {phone}"}
            
            elif action == "call_end":
                logger.info(f"[CALL] Ending call on {device_id}")
                return {"status": "success", "message": "Call ended"}
            
            elif action == "whatsapp_send":
                phone = command.get("data", {}).get("phone", "")
                message = command.get("data", {}).get("message", "")
                logger.info(f"[WHATSAPP] Sending to {phone} on {device_id}")
                return {"status": "success", "message": f"WhatsApp sent to {phone}"}
            
            elif action == "notifications_read":
                logger.info(f"[NOTIFICATIONS] Reading on {device_id}")
                return {
                    "status": "success",
                    "data": [
                        {"app": "Telegram", "text": "Nuovo messaggio"},
                        {"app": "WhatsApp", "text": "Messaggio da Marco"}
                    ]
                }
            
            else:
                logger.warning(f"[DEVICE] Unknown action: {action}")
                return {
                    "status": "error",
                    "message": f"Unknown action: {action}"
                }
        
        except Exception as e:
            logger.error(f"[DEVICE] Error sending command: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    @staticmethod
    async def update_heartbeat(device_id: str) -> None:
        """Aggiorna il timestamp dell'ultimo heartbeat"""
        if device_id in CONNECTED_DEVICES:
            import time
            CONNECTED_DEVICES[device_id]["last_heartbeat"] = time.time()
            logger.debug(f"[HEARTBEAT] {device_id}")

# Funzioni pubbliche
def is_device_connected(device_id: str) -> bool:
    """Versione sincrona per compatibilità"""
    return DeviceHub.is_device_connected(device_id)

def list_devices() -> List[str]:
    """Versione sincrona per compatibilità"""
    return DeviceHub.list_devices()

async def send_command(device_id: str, command: Dict) -> Dict[str, Any]:
    """Versione asincrona per invio comandi"""
    return await DeviceHub.send_command(device_id, command)

# WebSocket handler per registrazione device (aggiungere a main.py)
async def handle_device_websocket(websocket, device_id: str):
    """
    Handler WebSocket per device Android
    Endpoint: /ws/device/{device_id}
    """
    await DeviceHub.register_device(device_id, {
        "platform": "android",
        "connected": True
    })
    
    try:
        async for message in websocket.iter_text():
            import json
            data = json.loads(message)
            msg_type = data.get("type", "")
            
            if msg_type == "heartbeat":
                await DeviceHub.update_heartbeat(device_id)
            elif msg_type == "response":
                logger.debug(f"[DEVICE] Response from {device_id}: {data.get('status')}")
    
    except Exception as e:
        logger.error(f"[WS] Error with device {device_id}: {e}")
    
    finally:
        if device_id in CONNECTED_DEVICES:
            CONNECTED_DEVICES[device_id]["connected"] = False
            logger.info(f"[DEVICE] Disconnected: {device_id}")
