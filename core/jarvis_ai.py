import logging
from typing import Dict, Any, Optional
import re
from services.weather.weather_api import WeatherAPI

logger = logging.getLogger(__name__)

class JarvisAI:
    """Core AI per processare i comandi"""
    
    def __init__(self):
        self.weather_api = WeatherAPI()
        self.device_hub = None
        self.last_contact_name = None
        self.last_contact_phone = None
    
    async def process_command(self, command: str, device_id: str = None) -> Dict[str, Any]:
        """
        Processa un comando testuale
        Supporta: meteo, chiamate, whatsapp, notifiche
        """
        try:
            command = command.strip().lower()
            
            # ===== COMANDI METEO =====
            if any(word in command for word in ["meteo", "tempo", "temperatura", "clima"]):
                return await self._handle_weather(command)
            
            # ===== COMANDI TELEFONICI =====
            elif any(word in command for word in ["chiama", "call", "telefona"]):
                if any(word in command for word in ["chiama ", "call "]):
                    parts = re.split(r'(chiama|call)\s+', command, flags=re.IGNORECASE)
                    if len(parts) > 2:
                        contact = parts[2].strip()
                        return await self._handle_call(contact, device_id, call_type="phone")
            
            # ===== COMANDI WHATSAPP =====
            elif any(word in command for word in ["whatsapp", "messaggio", "manda", "invia"]):
                if any(word in command for word in ["whatsapp ", "messaggio "]):
                    parts = re.split(r'(whatsapp|messaggio)\s+', command, flags=re.IGNORECASE)
                    if len(parts) > 2:
                        rest = parts[2].strip()
                        return await self._handle_whatsapp(rest, device_id)
            
            # ===== COMANDI NOTIFICHE =====
            elif any(word in command for word in ["notifiche", "notifica", "messaggi"]):
                return await self._handle_notifications(device_id)
            
            # ===== COMANDI INFO =====
            elif any(word in command for word in ["chi sei", "help", "aiuto", "cosa puoi fare"]):
                return {
                    "status": "success",
                    "response": "Sono JARVIS, l'assistente vocale intelligente. Posso:\n"
                                "📞 Fare chiamate: 'chiama Marco' o 'chiama +39 123 456 789'\n"
                                "💬 Inviare messaggi WhatsApp: 'whatsapp Marco ciao'\n"
                                "🌤️ Informazioni meteo: 'meteo Roma'\n"
                                "📱 Leggere notifiche: 'notifiche'\n"
                                "Quale comando desideri?"
                }
            
            else:
                return {
                    "status": "error",
                    "response": "❌ Comando non riconosciuto. Prova:\n"
                                "'chiama Marco'\n"
                                "'meteo Roma'\n"
                                "'whatsapp Marco ciao'"
                }
        
        except Exception as e:
            logger.error(f"Error processing command: {e}")
            return {
                "status": "error",
                "response": f"❌ Errore: {str(e)}"
            }
    
    async def _handle_weather(self, command: str) -> Dict[str, Any]:
        """Gestisce i comandi meteo"""
        try:
            city = self._extract_city(command)
            
            if not city:
                return {
                    "status": "error",
                    "response": "❌ Quale città? Prova: 'meteo Roma'"
                }
            
            weather = await self.weather_api.get_weather(city)
            
            if weather["status"] == "success":
                data = weather["data"]
                response = (
                    f"🌤️ **{data['city']}**\n"
                    f"🌡️ Temperatura: {data['temperature']}°C\n"
                    f"💧 Umidità: {data['humidity']}%\n"
                    f"💨 Vento: {data['wind_speed']} km/h\n"
                    f"👁️ Visibilità: {data['visibility']} km\n"
                    f"📝 Condizioni: {data['description']}"
                )
                return {
                    "status": "success",
                    "response": response,
                    "data": weather["data"]
                }
            else:
                return weather
        
        except Exception as e:
            logger.error(f"Weather error: {e}")
            return {
                "status": "error",
                "response": f"❌ Errore meteo: {str(e)}"
            }
    
    async def _handle_call(self, contact: str, device_id: str, call_type: str = "phone") -> Dict[str, Any]:
        """Gestisce le chiamate"""
        try:
            if not device_id or device_id not in self._get_connected_devices():
                return {
                    "status": "error",
                    "response": "❌ Device non connesso. Accendi l'app Android!"
                }
            
            is_number = bool(re.match(r'^[0-9+\s\-()]*$', contact))
            
            if is_number:
                phone = contact.strip()
                self.last_contact_phone = phone
                contact_display = phone
            else:
                phone = contact.strip()
                self.last_contact_name = contact
                contact_display = f"{contact} ({phone})"
            
            clean_phone = re.sub(r'[^0-9+]', '', phone)
            
            if call_type == "phone":
                await self.device_hub.send_command(device_id, {
                    "type": "command",
                    "action": "call_start",
                    "id": "call_" + str(__import__('time').time()),
                    "data": {
                        "phone": clean_phone,
                        "contact_name": self.last_contact_name if not is_number else None
                    }
                })
                
                return {
                    "status": "success",
                    "response": f"📞 Sto chiamando {contact_display}..."
                }
            
            elif call_type == "whatsapp":
                await self.device_hub.send_command(device_id, {
                    "type": "command",
                    "action": "whatsapp_send",
                    "id": "whats_" + str(__import__('time').time()),
                    "data": {
                        "phone": clean_phone,
                        "message": "",
                        "contact_name": self.last_contact_name if not is_number else None
                    }
                })
                
                return {
                    "status": "success",
                    "response": f"💬 Aprendo WhatsApp con {contact_display}..."
                }
        
        except Exception as e:
            logger.error(f"Call error: {e}")
            return {
                "status": "error",
                "response": f"❌ Errore chiamata: {str(e)}"
            }
    
    async def _handle_whatsapp(self, command: str, device_id: str) -> Dict[str, Any]:
        """Gestisce i messaggi WhatsApp"""
        try:
            if not device_id or device_id not in self._get_connected_devices():
                return {
                    "status": "error",
                    "response": "❌ Device non connesso!"
                }
            
            parts = command.split(None, 1)
            
            if len(parts) < 1:
                return {
                    "status": "error",
                    "response": "❌ Usa: whatsapp Marco ciao"
                }
            
            contact = parts[0]
            message = parts[1] if len(parts) > 1 else ""
            
            clean_contact = re.sub(r'[^0-9+ ]', '', contact)
            
            await self.device_hub.send_command(device_id, {
                "type": "command",
                "action": "whatsapp_send",
                "id": "whats_" + str(__import__('time').time()),
                "data": {
                    "phone": clean_contact,
                    "message": message,
                    "contact_name": contact if not re.match(r'^[0-9+\s\-()]*$', contact) else None
                }
            })
            
            return {
                "status": "success",
                "response": f"💬 Inviando messaggio WhatsApp a {contact}...\nMessaggio: '{message}'"
            }
        
        except Exception as e:
            logger.error(f"WhatsApp error: {e}")
            return {
                "status": "error",
                "response": f"❌ Errore WhatsApp: {str(e)}"
            }
    
    async def _handle_notifications(self, device_id: str) -> Dict[str, Any]:
        """Gestisce la lettura delle notifiche"""
        try:
            if not device_id or device_id not in self._get_connected_devices():
                return {
                    "status": "error",
                    "response": "❌ Device non connesso!"
                }
            
            result = await self.device_hub.send_command(device_id, {
                "type": "command",
                "action": "notifications_read",
                "id": "notif_" + str(__import__('time').time())
            })
            
            return {
                "status": "success",
                "response": f"📱 Notifiche: {result}"
            }
        
        except Exception as e:
            logger.error(f"Notifications error: {e}")
            return {
                "status": "error",
                "response": f"❌ Errore notifiche: {str(e)}"
            }
    
    def _extract_city(self, command: str) -> Optional[str]:
        """Estrae il nome della città dal comando"""
        match = re.search(r'(?:meteo|tempo|temperatura|clima)\s+([A-Za-zÀ-ÿ\s]+)', command, re.IGNORECASE)
        
        if match:
            city = match.group(1).strip()
            return ' '.join(word.capitalize() for word in city.split())
        
        return None
    
    def _get_connected_devices(self) -> list:
        """Ottiene lista dei device connessi"""
        if self.device_hub:
            return self.device_hub.list_devices()
        return []
    
    def set_device_hub(self, device_hub):
        """Imposta il device hub"""
        self.device_hub = device_hub