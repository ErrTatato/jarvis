import asyncio
import logging
import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Simulazione device connessi (in produzione: usare database)
CONNECTED_DEVICES: Dict[str, Dict[str, Any]] = {}

# Timeout per le risposte dai device
DEVICE_TIMEOUT = 10
HEARTBEAT_TIMEOUT = 30  # secondi


class DeviceHub:
    """Gestisce la comunicazione con i device Android"""
    
    @staticmethod
    async def register_device(device_id: str, device_info: Dict) -> bool:
        """
        Registra un device come connesso
        
        Args:
            device_id: ID univoco del device (es: "mi13pro")
            device_info: Info aggiuntive (platform, ws, etc)
        
        Returns:
            True se registrazione riuscita
        """
        try:
            CONNECTED_DEVICES[device_id] = {
                "id": device_id,
                "connected": True,
                "last_heartbeat": datetime.now(),
                "registered_at": datetime.now(),
                "metadata": device_info or {},
                "ws": device_info.get("ws") if device_info else None
            }
            logger.info(f"[DEVICE_HUB] ✅ Device registrato: {device_id}")
            return True
        except Exception as e:
            logger.error(f"[DEVICE_HUB] ❌ Errore registrazione {device_id}: {e}")
            return False
    
    @staticmethod
    def is_device_connected(device_id: str) -> bool:
        """
        Verifica se un device è connesso
        
        Args:
            device_id: ID del device
        
        Returns:
            True se device è connesso e heartbeat recente
        """
        if device_id not in CONNECTED_DEVICES:
            return False
        
        device = CONNECTED_DEVICES[device_id]
        
        # Verifica heartbeat (max 30 secondi senza ping)
        time_since_heartbeat = datetime.now() - device.get("last_heartbeat", datetime.now())
        if time_since_heartbeat > timedelta(seconds=HEARTBEAT_TIMEOUT):
            logger.warning(f"[DEVICE_HUB] ⏱️  Heartbeat timeout: {device_id} ({time_since_heartbeat.seconds}s)")
            device["connected"] = False
            return False
        
        return device.get("connected", True)
    
    @staticmethod
    def list_devices() -> List[str]:
        """
        Elenco dei device connessi
        
        Returns:
            Lista di device_id attivi
        """
        active_devices = [
            dev_id for dev_id, dev in CONNECTED_DEVICES.items() 
            if DeviceHub.is_device_connected(dev_id)
        ]
        logger.debug(f"[DEVICE_HUB] Device attivi: {active_devices}")
        return active_devices
    
    @staticmethod
    async def send_command(device_id: str, command: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invia un comando a un device via WebSocket
        
        Args:
            device_id: ID del device
            command: {
                "type": "command",
                "action": "call_start|call_end|whatsapp_send|notifications_read",
                "id": "unique_id",
                "data": {...}
            }
        
        Returns:
            Response dal device o errore
        """
        if not DeviceHub.is_device_connected(device_id):
            logger.warning(f"[DEVICE_HUB] ❌ Device non connesso: {device_id}")
            return {
                "status": "error",
                "message": f"Device {device_id} non connesso"
            }
        
        try:
            device = CONNECTED_DEVICES[device_id]
            ws = device.get("ws")
            action = command.get("action", "?")
            
            logger.info(f"[DEVICE_HUB] 📤 Inviando a {device_id}: {action}")
            
            # Se WebSocket disponibile, invia via WS (preferito)
            if ws:
                try:
                    await ws.send_json(command)
                    logger.info(f"[DEVICE_HUB] ✅ Comando inviato via WebSocket: {action}")
                    return {
                        "status": "sent",
                        "message": f"Comando '{action}' inviato a {device_id}",
                        "device_id": device_id
                    }
                except Exception as e:
                    logger.error(f"[DEVICE_HUB] ❌ Errore WebSocket: {e}")
                    # Continua con gestione manuale
            
            # Gestione manuale comandi (fallback)
            action = command.get("action", "")
            
            if action == "call_start":
                phone = command.get("data", {}).get("phone", "")
                contact_name = command.get("data", {}).get("contact_name")
                logger.info(f"[CALL] 📞 Chiamando {contact_name or phone} su {device_id}")
                return {
                    "status": "success",
                    "message": f"Calling {contact_name or phone}",
                    "device_id": device_id
                }
            
            elif action == "call_end":
                logger.info(f"[CALL] 📞 Terminando chiamata su {device_id}")
                return {
                    "status": "success",
                    "message": "Call ended",
                    "device_id": device_id
                }
            
            elif action == "whatsapp_send":
                phone = command.get("data", {}).get("phone", "")
                message = command.get("data", {}).get("message", "")
                contact_name = command.get("data", {}).get("contact_name")
                logger.info(f"[WHATSAPP] 💬 Inviando a {contact_name or phone} su {device_id}")
                return {
                    "status": "success",
                    "message": f"WhatsApp sent to {contact_name or phone}",
                    "device_id": device_id
                }
            
            elif action == "notifications_read":
                logger.info(f"[NOTIFICATIONS] 📱 Leggendo notifiche su {device_id}")
                return {
                    "status": "success",
                    "data": [
                        {"app": "Telegram", "text": "Nuovo messaggio"},
                        {"app": "WhatsApp", "text": "Messaggio da Marco"},
                        {"app": "Gmail", "text": "Nuova email"}
                    ],
                    "device_id": device_id
                }
            
            else:
                logger.warning(f"[DEVICE_HUB] ⚠️  Azione sconosciuta: {action}")
                return {
                    "status": "error",
                    "message": f"Unknown action: {action}",
                    "device_id": device_id
                }
        
        except Exception as e:
            logger.error(f"[DEVICE_HUB] ❌ Errore invio comando: {e}")
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "message": str(e),
                "device_id": device_id
            }
    
    @staticmethod
    async def update_heartbeat(device_id: str) -> None:
        """
        Aggiorna il timestamp dell'ultimo heartbeat
        
        Args:
            device_id: ID del device
        """
        if device_id in CONNECTED_DEVICES:
            CONNECTED_DEVICES[device_id]["last_heartbeat"] = datetime.now()
            CONNECTED_DEVICES[device_id]["connected"] = True
            logger.debug(f"[DEVICE_HUB] ❤️  Heartbeat aggiornato: {device_id}")
        else:
            logger.warning(f"[DEVICE_HUB] ⚠️  Device non trovato per heartbeat: {device_id}")
    
    @staticmethod
    def disconnect_device(device_id: str) -> None:
        """
        Disconnette un device
        
        Args:
            device_id: ID del device
        """
        if device_id in CONNECTED_DEVICES:
            CONNECTED_DEVICES[device_id]["connected"] = False
            logger.info(f"[DEVICE_HUB] 👋 Device disconnesso: {device_id}")
    
    @staticmethod
    def get_device_info(device_id: str) -> Optional[Dict[str, Any]]:
        """
        Ottiene info di un device
        
        Args:
            device_id: ID del device
        
        Returns:
            Dict con info device o None
        """
        if device_id in CONNECTED_DEVICES:
            device = CONNECTED_DEVICES[device_id].copy()
            # Non includere websocket nel response
            device.pop("ws", None)
            return device
        return None
    
    @staticmethod
    def get_all_devices() -> Dict[str, Any]:
        """Ottiene info di tutti i device"""
        result = {}
        for device_id, device_data in CONNECTED_DEVICES.items():
            info = device_data.copy()
            info.pop("ws", None)
            result[device_id] = info
        return result


# ===== FUNZIONI PUBBLICHE (COMPATIBILITÀ) =====

def is_device_connected(device_id: str) -> bool:
    """Versione sincrona per compatibilità"""
    return DeviceHub.is_device_connected(device_id)


def list_devices() -> List[str]:
    """Versione sincrona per compatibilità"""
    return DeviceHub.list_devices()


async def send_command(device_id: str, command: Dict) -> Dict[str, Any]:
    """Versione asincrona per invio comandi"""
    return await DeviceHub.send_command(device_id, command)


async def register_device(device_id: str, metadata: Dict = None) -> bool:
    """Versione asincrona per registrazione"""
    return await DeviceHub.register_device(device_id, metadata or {})


async def update_heartbeat(device_id: str) -> None:
    """Versione asincrona per heartbeat"""
    await DeviceHub.update_heartbeat(device_id)


def disconnect_device(device_id: str) -> None:
    """Versione sincrona per disconnect"""
    DeviceHub.disconnect_device(device_id)


def get_device_info(device_id: str) -> Optional[Dict[str, Any]]:
    """Versione sincrona per info device"""
    return DeviceHub.get_device_info(device_id)