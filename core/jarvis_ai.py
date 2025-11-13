import os
import asyncio
import json
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import openai
from device_handlers import DeviceCommandHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("JARVIS-AI")

# OpenAI Configuration
openai.api_key = os.getenv("OPENAI_API_KEY", "your-api-key-here")

class JarvisAI:
    """
    JARVIS AI Assistant - Gestisce NLU, Intent Recognition, Device Actions
    """
    
    def __init__(self):
        self.model = "gpt-3.5-turbo"
        self.device_hub = None
        logger.info("✅ JARVIS AI initialized")
    
    def set_device_hub(self, device_hub):
        """Set DeviceHub reference for device commands"""
        self.device_hub = device_hub
        logger.info("✅ DeviceHub reference set")
    
    async def process_input(self, text: str, websocket=None) -> str:
        """
        Main processing function
        1. Parse intent
        2. Extract entities
        3. Route to appropriate handler
        """
        try:
            logger.info(f"📨 Processing: {text}")
            
            # Parse intent and entities
            intent, entities, confidence = await self._parse_intent(text)
            
            if confidence < 0.5:
                return "Non ho capito bene. Puoi ripetere?"
            
            logger.info(f"🎯 Intent: {intent} (confidence: {confidence:.2f})")
            
            # ============== DEVICE ACTIONS ==============
            if intent in ["call", "whatsapp_send", "sms_send", "read_notifications"]:
                response = await self._handle_device_action(intent, entities)
                return response
            
            # ============== WEATHER ==============
            elif intent == "get_weather":
                response = await self._handle_weather()
                return response
            
            elif intent == "get_location_weather":
                city = entities.get("city", "Rome")
                response = await self._handle_location_weather(city)
                return response
            
            # ============== GENERAL AI ==============
            elif intent == "greeting":
                return "Ciao! Sono JARVIS, il tuo assistente vocale. Come posso aiutarti?"
            
            elif intent == "time":
                current_time = datetime.now().strftime("%H:%M:%S")
                return f"Sono le {current_time}"
            
            else:
                # Fall back to GPT for general queries
                response = await self._query_gpt(text)
                return response
        
        except Exception as e:
            logger.error(f"❌ Processing error: {e}", exc_info=True)
            return f"Errore durante l'elaborazione: {str(e)}"
    
    # ============== DEVICE ACTION HANDLER ==============
    
    async def _handle_device_action(self, intent: str, entities: Dict[str, Any]) -> str:
        """
        Route device commands to appropriate handlers
        """
        try:
            if not self.device_hub:
                logger.warning("⚠️ DeviceHub not initialized")
                return "Il dispositivo non è connesso"
            
            if intent == "call":
                contact = entities.get("contact_name", "")
                phone = entities.get("phone_number")
                
                if not contact:
                    return "Dimmi a chi vuoi chiamare"
                
                result = await DeviceCommandHandler.handle_call_command(
                    contact, phone, self.device_hub
                )
                return result.get("message", "Errore")
            
            elif intent == "whatsapp_send":
                contact = entities.get("contact_name", "")
                message = entities.get("message_content", "")
                phone = entities.get("phone_number")
                
                if not contact or not message:
                    return "Dimmi a chi inviare e cosa scrivere"
                
                result = await DeviceCommandHandler.handle_whatsapp_command(
                    contact, message, phone, self.device_hub
                )
                return result.get("message", "Errore")
            
            elif intent == "sms_send":
                contact = entities.get("contact_name", "")
                message = entities.get("message_content", "")
                phone = entities.get("phone_number")
                
                if not contact or not message:
                    return "Dimmi a chi inviare l'SMS e cosa scrivere"
                
                result = await DeviceCommandHandler.handle_sms_command(
                    contact, message, phone, self.device_hub
                )
                return result.get("message", "Errore")
            
            elif intent == "read_notifications":
                result = await DeviceCommandHandler.handle_notifications_command(
                    self.device_hub
                )
                return result.get("message", "Errore")
            
            return "Comando non riconosciuto"
        
        except Exception as e:
            logger.error(f"❌ Device action error: {e}", exc_info=True)
            return f"Errore: {str(e)}"
    
    # ============== WEATHER HANDLER ==============
    
    async def _handle_weather(self) -> str:
        """Get current weather"""
        try:
            logger.info("🌤️ Fetching weather...")
            # TODO: Implement weather API call
            return "La temperatura è di 15 gradi con cielo sereno"
        except Exception as e:
            logger.error(f"❌ Weather error: {e}")
            return "Non riesco a recuperare le informazioni meteo"
    
    async def _handle_location_weather(self, city: str) -> str:
        """Get weather for specific city"""
        try:
            logger.info(f"🌍 Fetching weather for {city}...")
            # TODO: Implement location weather API call
            return f"A {city} la temperatura è di 15 gradi"
        except Exception as e:
            logger.error(f"❌ Location weather error: {e}")
            return f"Non riesco a recuperare il meteo di {city}"
    
    # ============== NLU & INTENT DETECTION ==============
    
    async def _parse_intent(self, text: str) -> Tuple[str, Dict[str, Any], float]:
        """
        Parse user input and extract intent + entities
        Returns: (intent, entities, confidence)
        """
        try:
            text_lower = text.lower()
            
            # Simple rule-based intent matching
            intents_keywords = {
                "call": ["chiama", "telefono", "numero", "call"],
                "whatsapp_send": ["whatsapp", "invia", "messaggio", "chat"],
                "sms_send": ["sms", "messaggio testo"],
                "read_notifications": ["notifiche", "notification", "avvisi"],
                "get_weather": ["meteo", "temperature", "pioggia", "neve"],
                "get_location_weather": ["meteo", "tempo", "città"],
                "greeting": ["ciao", "salve", "hey", "hello"],
                "time": ["ora", "time", "quando"],
            }
            
            best_intent = None
            best_confidence = 0.0
            
            for intent, keywords in intents_keywords.items():
                for keyword in keywords:
                    if keyword in text_lower:
                        confidence = 0.9
                        if confidence > best_confidence:
                            best_confidence = confidence
                            best_intent = intent
                        break
            
            if not best_intent:
                best_intent = "general_query"
                best_confidence = 0.3
            
            # Extract entities
            entities = await self._extract_entities(text, best_intent)
            
            return best_intent, entities, best_confidence
        
        except Exception as e:
            logger.error(f"❌ Intent parsing error: {e}")
            return "general_query", {}, 0.0
    
    async def _extract_entities(self, text: str, intent: str) -> Dict[str, Any]:
        """
        Extract entities from user input based on intent
        """
        entities = {}
        text_lower = text.lower()
        
        try:
            if intent in ["call", "whatsapp_send", "sms_send"]:
                # Extract contact name (simple extraction)
                words = text_lower.split()
                
                # Look for prepositions
                for i, word in enumerate(words):
                    if word in ["a", "di", "per"] and i + 1 < len(words):
                        contact = words[i + 1]
                        if contact not in ["whatsapp", "sms", "chiama"]:
                            entities["contact_name"] = contact.capitalize()
                            break
                
                # Extract message content for WhatsApp/SMS
                if intent in ["whatsapp_send", "sms_send"]:
                    if ":" in text:
                        message_part = text.split(":", 1)[1].strip()
                        entities["message_content"] = message_part
            
            return entities
        
        except Exception as e:
            logger.error(f"❌ Entity extraction error: {e}")
            return entities
    
    # ============== GPT FALLBACK ==============
    
    async def _query_gpt(self, text: str) -> str:
        """
        Fallback to GPT for general queries
        """
        try:
            logger.info("🤖 Querying GPT...")
            
            response = await asyncio.to_thread(
                openai.ChatCompletion.create,
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are JARVIS, a helpful AI assistant. Answer in Italian."
                    },
                    {"role": "user", "content": text}
                ],
                max_tokens=200,
                temperature=0.7
            )
            
            reply = response.choices[0].message.content
            logger.info(f"✅ GPT reply: {reply}")
            return reply
        
        except Exception as e:
            logger.error(f"❌ GPT query error: {e}")
            return "Scusa, non riesco a elaborare la tua richiesta"

# Global instance
jarvis = JarvisAI()

async def process_user_input(text: str, websocket=None) -> str:
    """Public API for processing user input"""
    return await jarvis.process_input(text, websocket)

def init_jarvis(device_hub):
    """Initialize JARVIS with DeviceHub"""
    jarvis.set_device_hub(device_hub)
    logger.info("✅ JARVIS fully initialized")