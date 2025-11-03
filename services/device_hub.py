import logging
import asyncio
import uuid
from datetime import datetime
from typing import Dict

from fastapi import WebSocket, WebSocketDisconnect

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

devices_registry: Dict[str, datetime] = {}
HEARTBEAT_TIMEOUT = 20  # secondi

ws_connections: Dict[str, WebSocket] = {}
pending_replies: Dict[str, asyncio.Future] = {}

def register_device(device_id: str):
    devices_registry[device_id] = datetime.now()
    logger.info(f"[DEVICE_HUB] {device_id} registered")

def unregister_device(device_id: str):
    devices_registry.pop(device_id, None)
    ws_connections.pop(device_id, None)
    logger.info(f"[DEVICE_HUB] {device_id} unregistered")

def list_devices():
    now = datetime.now()
    active = []
    to_remove = []
    for device_id, last_seen in devices_registry.items():
        elapsed = (now - last_seen).total_seconds()
        if elapsed < HEARTBEAT_TIMEOUT:
            active.append(device_id)
        else:
            to_remove.append(device_id)
    for device_id in to_remove:
        devices_registry.pop(device_id, None)
        ws_connections.pop(device_id, None)
        logger.info(f"[DEVICE_HUB] {device_id} removed (timeout)")
    return active

def is_device_connected(device_id: str) -> bool:
    if device_id not in devices_registry:
        return False
    elapsed = (datetime.now() - devices_registry[device_id]).total_seconds()
    return elapsed < HEARTBEAT_TIMEOUT and device_id in ws_connections

async def ws_handler(websocket: WebSocket, device_id: str):
    await websocket.accept()
    ws_connections[device_id] = websocket
    register_device(device_id)
    logger.info(f"[WS] {device_id} connected")
    try:
        while True:
            msg = await websocket.receive_json()
            mtype = msg.get("type")
            if mtype == "heartbeat":
                register_device(device_id)
                continue
            if mtype == "response":
                cmd_id = msg.get("id")
                fut = pending_replies.pop(cmd_id, None)
                if fut and not fut.done():
                    fut.set_result(msg)
                continue
            if mtype == "event":
                register_device(device_id)
                logger.info(f"[EVENT] {device_id}: {msg.get('event')} -> {msg.get('data')}")
    except WebSocketDisconnect:
        logger.info(f"[WS] {device_id} disconnected")
    except Exception as e:
        logger.exception(f"[WS] {device_id} error: {e}")
    finally:
        unregister_device(device_id)

async def send_command(device_id: str, payload: dict, timeout: float = 12.0) -> dict:
    if device_id not in ws_connections:
        logger.warning(f"[CMD] device {device_id} not connected")
        return {"ok": False, "error": "not_connected"}

    ws = ws_connections[device_id]
    cmd_id = payload.get("id") or str(uuid.uuid4())
    payload["id"] = cmd_id
    payload.setdefault("type", "command")

    loop = asyncio.get_event_loop()
    fut: asyncio.Future = loop.create_future()
    pending_replies[cmd_id] = fut

    try:
        await ws.send_json(payload)
        logger.info(f"[CMD] -> {device_id}: {payload.get('action')}")
        resp = await asyncio.wait_for(fut, timeout=timeout)
        ok = bool(resp.get("ok", True))
        data = resp.get("data", {})
        return {"ok": ok, "data": data}
    except asyncio.TimeoutError:
        pending_replies.pop(cmd_id, None)
        logger.error(f"[CMD] timeout waiting reply from {device_id} for {payload.get('action')}")
        return {"ok": False, "error": "timeout"}
    except Exception as e:
        pending_replies.pop(cmd_id, None)
        logger.exception(f"[CMD] send error to {device_id}: {e}")
        return {"ok": False, "error": str(e)}
