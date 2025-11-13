import asyncio
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger("JARVIS-DeviceHandlers")

class DeviceCommandHandler:
    """
    Gestisce i comandi per il device Android
    Collega gli intenti JARVIS alle azioni sul device
    """
    
    @staticmethod
    async def handle_call_command(contact_name: str, phone: Optional[str] = None, device_hub=None) -> Dict[str, Any]:
        """
        Gestisce comando: Chiama [contatto]
        
        Args:
            contact_name: Nome contatto da cercare
            phone: Numero di telefono (opzionale)
            device_hub: Istanza DeviceHub per invio comando
        
        Returns:
            {
                "success": bool,
                "message": str,
                "action_type": "call"
            }
        """
        try:
            logger.info(f"🔴 Handling CALL command: {contact_name}")
            
            if not device_hub:
                logger.error("❌ DeviceHub not initialized")
                return {
                    "success": False,
                    "message": "Sistema non disponibile",
                    "action_type": "call"
                }
            
            # Se non abbiamo il numero, cercalo nella rubrica
            if not phone:
                phone = await DeviceCommandHandler._find_contact_phone(contact_name, device_hub)
                if not phone:
                    return {
                        "success": False,
                        "message": f"Non ho trovato il numero di {contact_name}",
                        "action_type": "call"
                    }
            
            # Invia comando al device
            device_id = "android_device_01"  # Modifica se necessario
            
            command = {
                "type": "command",
                "action": "call.start",
                "data": {
                    "phone": phone,
                    "contact_name": contact_name,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            logger.info(f"📤 Sending CALL command to device: {phone}")
            
            # Invia via WebSocket
            result = await device_hub.send_command(device_id, command)
            
            if result.get("success"):
                logger.info(f"✅ CALL initiated: {contact_name} ({phone})")
                return {
                    "success": True,
                    "message": f"Sto chiamando {contact_name}...",
                    "action_type": "call",
                    "data": {
                        "contact": contact_name,
                        "phone": phone
                    }
                }
            else:
                logger.error(f"❌ CALL failed: {result}")
                return {
                    "success": False,
                    "message": "Non riesco a effettuare la chiamata",
                    "action_type": "call"
                }
        
        except Exception as e:
            logger.error(f"❌ CALL error: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Errore: {str(e)}",
                "action_type": "call"
            }
    
    @staticmethod
    async def handle_whatsapp_command(contact_name: str, message: str, phone: Optional[str] = None, device_hub=None) -> Dict[str, Any]:
        """
        Gestisce comando: Invia WhatsApp a [contatto] messaggio: [messaggio]
        
        Args:
            contact_name: Nome contatto
            message: Messaggio da inviare
            phone: Numero WhatsApp (opzionale)
            device_hub: Istanza DeviceHub
        
        Returns:
            {
                "success": bool,
                "message": str,
                "action_type": "whatsapp"
            }
        """
        try:
            logger.info(f"💬 Handling WHATSAPP command: {contact_name}")
            
            if not device_hub:
                logger.error("❌ DeviceHub not initialized")
                return {
                    "success": False,
                    "message": "Sistema non disponibile",
                    "action_type": "whatsapp"
                }
            
            if not phone:
                phone = await DeviceCommandHandler._find_contact_phone(contact_name, device_hub)
                if not phone:
                    return {
                        "success": False,
                        "message": f"Non ho trovato il numero di {contact_name}",
                        "action_type": "whatsapp"
                    }
            
            device_id = "android_device_01"
            
            command = {
                "type": "command",
                "action": "whatsapp.send",
                "data": {
                    "phone": phone,
                    "contact_name": contact_name,
                    "message": message,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            logger.info(f"📤 Sending WHATSAPP message to: {contact_name}")
            
            result = await device_hub.send_command(device_id, command)
            
            if result.get("success"):
                logger.info(f"✅ WhatsApp message sent to {contact_name}")
                return {
                    "success": True,
                    "message": f"Messaggio WhatsApp inviato a {contact_name}",
                    "action_type": "whatsapp",
                    "data": {
                        "contact": contact_name,
                        "message": message
                    }
                }
            else:
                return {
                    "success": False,
                    "message": "Non riesco a inviare il messaggio",
                    "action_type": "whatsapp"
                }
        
        except Exception as e:
            logger.error(f"❌ WHATSAPP error: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Errore: {str(e)}",
                "action_type": "whatsapp"
            }
    
    @staticmethod
    async def handle_sms_command(contact_name: str, message: str, phone: Optional[str] = None, device_hub=None) -> Dict[str, Any]:
        """
        Gestisce comando: Invia SMS a [contatto]
        """
        try:
            logger.info(f"📱 Handling SMS command: {contact_name}")
            
            if not device_hub:
                return {"success": False, "message": "Sistema non disponibile", "action_type": "sms"}
            
            if not phone:
                phone = await DeviceCommandHandler._find_contact_phone(contact_name, device_hub)
                if not phone:
                    return {"success": False, "message": f"Non ho trovato il numero di {contact_name}", "action_type": "sms"}
            
            device_id = "android_device_01"
            
            command = {
                "type": "command",
                "action": "sms.send",
                "data": {
                    "phone": phone,
                    "contact_name": contact_name,
                    "message": message,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            result = await device_hub.send_command(device_id, command)
            
            if result.get("success"):
                logger.info(f"✅ SMS sent to {contact_name}")
                return {
                    "success": True,
                    "message": f"SMS inviato a {contact_name}",
                    "action_type": "sms"
                }
            else:
                return {"success": False, "message": "Non riesco a inviare l'SMS", "action_type": "sms"}
        
        except Exception as e:
            logger.error(f"❌ SMS error: {e}")
            return {"success": False, "message": f"Errore: {str(e)}", "action_type": "sms"}
    
    @staticmethod
    async def handle_notifications_command(device_hub=None) -> Dict[str, Any]:
        """
        Gestisce comando: Leggi notifiche
        """
        try:
            logger.info("📬 Handling READ NOTIFICATIONS command")
            
            if not device_hub:
                return {"success": False, "message": "Sistema non disponibile", "action_type": "notifications"}
            
            device_id = "android_device_01"
            
            command = {
                "type": "command",
                "action": "notifications.read",
                "data": {"timestamp": datetime.now().isoformat()}
            }
            
            result = await device_hub.send_command(device_id, command)
            
            if result.get("success"):
                notifications = result.get("data", {}).get("notifications", [])
                logger.info(f"✅ Retrieved {len(notifications)} notifications")
                
                if not notifications:
                    return {
                        "success": True,
                        "message": "Non hai notifiche",
                        "action_type": "notifications",
                        "data": {"count": 0}
                    }
                
                # Formatta le notifiche
                summary = f"Hai {len(notifications)} notifiche:\n"
                for notif in notifications[:5]:
                    app = notif.get("app", "App")
                    text = notif.get("text", "")[:100]  # Limita a 100 caratteri
                    summary += f"- {app}: {text}\n"
                
                return {
                    "success": True,
                    "message": summary,
                    "action_type": "notifications",
                    "data": {
                        "count": len(notifications),
                        "notifications": notifications
                    }
                }
            else:
                return {"success": False, "message": "Non riesco a leggere le notifiche", "action_type": "notifications"}
        
        except Exception as e:
            logger.error(f"❌ NOTIFICATIONS error: {e}")
            return {"success": False, "message": f"Errore: {str(e)}", "action_type": "notifications"}
    
    @staticmethod
    async def _find_contact_phone(contact_name: str, device_hub=None) -> Optional[str]:
        """
        Trova il numero di telefono di un contatto nella rubrica del device
        """
        try:
            if not device_hub:
                return None
            
            device_id = "android_device_01"
            
            command = {
                "type": "query",
                "action": "contact.find",
                "data": {"name": contact_name}
            }
            
            logger.info(f"🔍 Searching for contact: {contact_name}")
            result = await device_hub.send_command(device_id, command)
            
            if result.get("success") and result.get("data"):
                phone = result.get("data", {}).get("phone")
                logger.info(f"✅ Found phone for {contact_name}: {phone}")
                return phone
            
            logger.warning(f"⚠️ Contact not found: {contact_name}")
            return None
        
        except Exception as e:
            logger.error(f"❌ Error finding contact: {e}")
            return None