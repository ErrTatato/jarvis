# services/device_hub.py
import logging
import asyncio
import uuid
from datetime import datetime
from typing import Dict, Optional
from fastapi import WebSocket, WebSocketDisconnect

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

devices_registry: Dict[str, datetime] = {}
ws_connections: Dict[str, WebSocket] = {}
pending_replies: Dict[str, asyncio.Future] = {}

HEARTBEAT_TIMEOUT = 20  # secondi

def register_device(device_id: str):
    """Registra o aggiorna heartbeat del device"""
    devices_registry[device_id] = datetime.now()
    logger.info(f"[DEVICE_HUB] {device_id} registered")

def unregister_device(device_id: str):
    """Rimuove device"""
    devices_registry.pop(device_id, None)
    ws_connections.pop(device_id, None)
    logger.info(f"[DEVICE_HUB] {device_id} unregistered")

def is_device_connected(device_id: str) -> bool:
    """Controlla se device è connesso via WS"""
    return device_id in ws_connections

def list_devices() -> list:
    """Lista device attivi"""
    now = datetime.now()
    active = []
    to_remove = []
    
    for device_id, last_seen in list(devices_registry.items()):
        elapsed = (now - last_seen).total_seconds()
        if elapsed < HEARTBEAT_TIMEOUT:
            active.append(device_id)
        else:
            to_remove.append(device_id)
    
    for device_id in to_remove:
        unregister_device(device_id)
    
    return active

async def send_command(device_id: str, command: dict) -> dict:
    """Invia comando al device e aspetta risposta"""
    if device_id not in ws_connections:
        return {"ok": False, "error": "device_not_connected"}
    
    cmd_id = str(uuid.uuid4())
    command["id"] = cmd_id
    
    # Crea Future per aspettare la risposta
    future = asyncio.Future()
    pending_replies[cmd_id] = future
    
    try:
        # Invia comando
        ws = ws_connections[device_id]
        await ws.send_json(command)
        logger.info(f"[DEVICE_HUB] Sent to {device_id}: {command.get('action', '?')}")
        
        # Aspetta risposta con timeout
        response = await asyncio.wait_for(future, timeout=10.0)
        return response
    except asyncio.TimeoutError:
        return {"ok": False, "error": "timeout"}
    except Exception as e:
        logger.error(f"[DEVICE_HUB] send_command error: {e}")
        return {"ok": False, "error": str(e)}
    finally:
        pending_replies.pop(cmd_id, None)

async def ws_handler(websocket: WebSocket, device_id: str):
    """Handler WebSocket per device connesso"""
    await websocket.accept()
    ws_connections[device_id] = websocket
    register_device(device_id)
    logger.info(f"[WS] {device_id} connected")
    
    try:
        while True:
            # Ricevi messaggio dal device
            data = await websocket.receive_json()
            
            # Gestisci heartbeat
            if data.get("type") == "heartbeat":
                register_device(device_id)
                logger.debug(f"[WS] {device_id} heartbeat")
                continue
            
            # Gestisci response a comando inviato
            if data.get("type") == "response":
                cmd_id = data.get("id")
                if cmd_id in pending_replies:
                    future = pending_replies[cmd_id]
                    if not future.done():
                        future.set_result(data)
                    logger.info(f"[WS] {device_id} response: {data.get('ok')}")
                continue
            
            logger.debug(f"[WS] {device_id} message: {data}")
    
    except WebSocketDisconnect:
        logger.info(f"[WS] {device_id} disconnected")
    except Exception as e:
        logger.error(f"[WS] {device_id} error: {e}")
    finally:
        unregister_device(device_id)
