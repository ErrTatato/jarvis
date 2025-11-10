# core/jarvis_ai.py - MAIN AI CORE WITH INTEGRATED COMMANDS
import logging
import json
from typing import Optional, Dict
from datetime import datetime

logger = logging.getLogger(__name__)

class JarvisAI:
    """Main AI Core for JARVIS"""
    
    def __init__(self):
        self.device_id = "mi13pro"
        self.logger = logging.getLogger("JarvisAI")
        
    async def process_text(self, user_input: str, device_id: str = None) -> str:
        """
        Processa il testo dell'utente e restituisce una risposta
        Supporta:
        - Comandi telefono (chiama, whatsapp)
        - Meteo
        - Info generiche
        """
        device_id = device_id or self.device_id
        user_input_lower = user_input.lower().strip()
        
        # ===== METEO =====
        if any(word in user_input_lower for word in ["meteo", "tempo", "pioggia", "temperatura", "weather"]):
            return await self._handle_weather(user_input)
        
        # ===== CHIAMATE =====
        elif "chiama" in user_input_lower:
            return await self._handle_call(user_input, device_id)
        
        # ===== WHATSAPP =====
        elif "whatsapp" in user_input_lower or "messaggio" in user_input_lower:
            return await self._handle_whatsapp(user_input, device_id)
        
        # ===== NOTIFICHE =====
        elif "notif" in user_input_lower:
            return await self._handle_notifications(device_id)
        
        # ===== INFO GENERICHE =====
        elif any(word in user_input_lower for word in ["chi sei", "cosa sei", "help", "aiuto"]):
            return self._handle_info()
        
        # ===== DEFAULT =====
        else:
            return f"Ho ricevuto: {user_input}. Prova 'meteo Roma', 'chiama [numero]', 'whatsapp [numero]', etc."
    
    async def _handle_weather(self, user_input: str) -> str:
        """Gestisci richieste meteo"""
        try:
            from services.weather.weather_api import get_weather, format_weather_response
            
            # Estrai città (semplicissimo parsing)
            words = user_input.split()
            city = words[-1] if len(words) > 1 else "Roma"
            
            self.logger.info(f"[WEATHER] Fetching weather for: {city}")
            weather = await get_weather(city, "metric")
            
            if "error" in weather:
                return f"❌ Non riesco a recuperare il meteo per {city}"
            
            return format_weather_response(weather, "metric")
        
        except Exception as e:
            self.logger.error(f"[WEATHER] Error: {e}")
            return f"❌ Errore nel recupero del meteo: {str(e)}"
    
    async def _handle_call(self, user_input: str, device_id: str) -> str:
        """Gestisci richieste di chiamata"""
        try:
            # Estrai numero (semplice regex)
            import re
            numbers = re.findall(r'\+?\d{1,4}[\s.-]?\d{1,4}[\s.-]?\d{1,9}', user_input)
            
            if not numbers:
                return "❌ Non ho trovato un numero di telefono valido. Usa: 'chiama +39 123 456789'"
            
            phone = numbers[0].replace(" ", "").replace("-", "").replace(".", "")
            
            from services.device_hub import send_command, is_device_connected
            
            if not is_device_connected(device_id):
                return "❌ Il device non è connesso"
            
            self.logger.info(f"[CALL] Calling: {phone}")
            result = await send_command(
                device_id,
                {"type": "command", "action": "call_start", "data": {"phone": phone}}
            )
            
            if result.get("status") == "success":
                return f"✅ Sto chiamando {phone}"
            else:
                return f"❌ Errore nella chiamata: {result.get('message', 'Unknown error')}"
        
        except Exception as e:
            self.logger.error(f"[CALL] Error: {e}")
            return f"❌ Errore durante la chiamata: {str(e)}"
    
    async def _handle_whatsapp(self, user_input: str, device_id: str) -> str:
        """Gestisci richieste WhatsApp"""
        try:
            import re
            
            # Estrai numero e messaggio
            # Formato: "whatsapp +39123 ciao tizio"
            parts = user_input.split()
            numbers = re.findall(r'\+?\d{1,4}[\s.-]?\d{1,4}[\s.-]?\d{1,9}', user_input)
            
            if not numbers:
                return "❌ Numero mancante. Usa: 'whatsapp +39 123456789 tuo messaggio'"
            
            phone = numbers[0].replace(" ", "").replace("-", "").replace(".", "")
            
            # Estrai messaggio (tutto dopo il numero)
            message = user_input[user_input.find(phone) + len(phone):].strip()
            if not message:
                message = "Ciao"
            
            from services.device_hub import send_command, is_device_connected
            
            if not is_device_connected(device_id):
                return "❌ Il device non è connesso"
            
            self.logger.info(f"[WHATSAPP] Sending to {phone}: {message}")
            result = await send_command(
                device_id,
                {"type": "command", "action": "whatsapp_send", "data": {"phone": phone, "message": message}}
            )
            
            if result.get("status") == "success":
                return f"✅ Messaggio inviato a {phone}: '{message}'"
            else:
                return f"❌ Errore nell'invio: {result.get('message', 'Unknown error')}"
        
        except Exception as e:
            self.logger.error(f"[WHATSAPP] Error: {e}")
            return f"❌ Errore WhatsApp: {str(e)}"
    
    async def _handle_notifications(self, device_id: str) -> str:
        """Gestisci richieste notifiche"""
        try:
            from services.device_hub import send_command, is_device_connected
            
            if not is_device_connected(device_id):
                return "❌ Il device non è connesso"
            
            self.logger.info("[NOTIFICATIONS] Reading notifications")
            result = await send_command(
                device_id,
                {"type": "command", "action": "notifications_read", "data": {}}
            )
            
            if result.get("status") == "success":
                notifications = result.get("data", [])
                if not notifications:
                    return "✅ Nessuna notifica"
                
                response = "📬 Ultime notifiche:\n"
                for notif in notifications[:5]:
                    response += f"- {notif.get('app', 'Unknown')}: {notif.get('text', '')}\n"
                return response
            else:
                return f"❌ Errore nel lettura notifiche: {result.get('message', 'Unknown error')}"
        
        except Exception as e:
            self.logger.error(f"[NOTIFICATIONS] Error: {e}")
            return f"❌ Errore notifiche: {str(e)}"
    
    def _handle_info(self) -> str:
        """Restituisci info su JARVIS"""
        return """
🤖 Ciao! Sono JARVIS v2.3.0

📋 Comandi disponibili:
- 'meteo [città]' → Ottieni il meteo
- 'chiama [numero]' → Chiama un numero
- 'whatsapp [numero] [messaggio]' → Invia WhatsApp
- 'notifiche' → Leggi notifiche

💡 Esempi:
→ "meteo Milano"
→ "chiama +39 123 456 789"
→ "whatsapp +39 333 1234567 Ciao!"
"""
    
    async def transcribe_audio(self, audio_data: bytes) -> Optional[str]:
        """Trascrivi audio (richiede Whisper o SpeechRecognition)"""
        try:
            # TODO: Implementare con Whisper o Google Speech-to-Text
            return "Comando audio ricevuto"
        except Exception as e:
            self.logger.error(f"[TRANSCRIBE] Error: {e}")
            return None
    
    async def speak_response(self, response: str) -> None:
        """Riproduci risposta con TTS"""
        try:
            # TODO: Implementare con ElevenLabs o gTTS
            self.logger.info(f"[TTS] {response}")
        except Exception as e:
            self.logger.error(f"[TTS] Error: {e}")
