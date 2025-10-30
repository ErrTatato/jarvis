import asyncio
from typing import Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException

router = APIRouter()
connections: Dict[str, WebSocket] = {}
pending: Dict[str, asyncio.Future] = {}

@router.websocket("/ws/device")
async def ws_device(ws: WebSocket, device_id: str):
    await ws.accept()
    connections[device_id] = ws
    print(f"[DEVICE_HUB] {device_id} connected")
    try:
        while True:
            msg = await ws.receive_json()
            reply_to = msg.get("reply_to")
            if reply_to and reply_to in pending:
                fut = pending.pop(reply_to)
                if not fut.done():
                    fut.set_result(msg)
    except WebSocketDisconnect:
        print(f"[DEVICE_HUB] {device_id} disconnected")
    finally:
        if device_id in connections and connections[device_id] is ws:
            del connections[device_id]

async def send_command(device_id: str, payload: Dict[str, Any], timeout: float = 12.0):
    ws = connections.get(device_id)
    if not ws:
        raise HTTPException(status_code=404, detail="device offline")
    cmd_id = payload.get("id") or str(id(payload))
    payload["id"] = cmd_id
    fut: asyncio.Future = asyncio.get_event_loop().create_future()
    pending[cmd_id] = fut
    await ws.send_json(payload)
    try:
        return await asyncio.wait_for(fut, timeout=timeout)
    except asyncio.TimeoutError:
        pending.pop(cmd_id, None)
        raise HTTPException(status_code=504, detail="device timeout")

def list_devices():
    return list(connections.keys())
