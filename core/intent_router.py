import logging
from typing import Dict, Tuple, Any

logger = logging.getLogger("JARVIS-IntentRouter")

class IntentRouter:
    """
    Routes user intents to appropriate handlers
    Uses keyword matching with confidence scoring
    """
    
    # Define all intents with keywords and confidence thresholds
    intents = {
        # ========== DEVICE ACTIONS ==========
        "call": {
            "keywords": ["chiama", "telefono", "numero", "call", "chiamare"],
            "confidence": 0.90,
            "type": "device"
        },
        "whatsapp_send": {
            "keywords": ["whatsapp", "invia", "messaggio", "chat", "wp"],
            "confidence": 0.85,
            "type": "device"
        },
        "sms_send": {
            "keywords": ["sms", "messaggio testo", "testo"],
            "confidence": 0.85,
            "type": "device"
        },
        "read_notifications": {
            "keywords": ["notifiche", "notification", "avvisi", "alert"],
            "confidence": 0.80,
            "type": "device"
        },
        
        # ========== WEATHER ==========
        "get_weather": {
            "keywords": ["meteo", "temperatura", "pioggia", "neve", "tempo"],
            "confidence": 0.85,
            "type": "weather"
        },
        "get_location_weather": {
            "keywords": ["meteo", "temperatura", "città", "provincia"],
            "confidence": 0.80,
            "type": "weather"
        },
        
        # ========== AI RESPONSES ==========
        "greeting": {
            "keywords": ["ciao", "salve", "hey", "hello", "buongiorno", "buonasera"],
            "confidence": 0.95,
            "type": "ai"
        },
        "time": {
            "keywords": ["ora", "time", "quando", "che ora"],
            "confidence": 0.90,
            "type": "ai"
        },
        "help": {
            "keywords": ["aiuto", "help", "cosa puoi fare", "comandi"],
            "confidence": 0.85,
            "type": "ai"
        },
    }
    
    @staticmethod
    def route_intent(user_input: str) -> Tuple[str, Dict[str, Any], float]:
        """
        Route user input to appropriate intent
        
        Args:
            user_input: Raw user text input
        
        Returns:
            Tuple of (intent_name, metadata, confidence_score)
        """
        try:
            text_lower = user_input.lower()
            best_intent = None
            best_confidence = 0.0
            best_metadata = {}
            
            logger.debug(f"🔍 Routing intent for: {user_input}")
            
            # Check each intent
            for intent_name, intent_data in IntentRouter.intents.items():
                keywords = intent_data.get("keywords", [])
                intent_confidence = intent_data.get("confidence", 0.5)
                
                # Check if any keyword matches
                for keyword in keywords:
                    if keyword in text_lower:
                        # Calculate actual confidence based on match position
                        match_count = text_lower.count(keyword)
                        actual_confidence = intent_confidence * (0.9 + (match_count - 1) * 0.05)
                        
                        logger.debug(f"  ✓ {intent_name}: {actual_confidence:.2f}")
                        
                        if actual_confidence > best_confidence:
                            best_confidence = actual_confidence
                            best_intent = intent_name
                            best_metadata = {
                                "type": intent_data.get("type", "unknown"),
                                "matched_keyword": keyword,
                                "match_count": match_count
                            }
                        break
            
            # If no intent matched, return generic
            if not best_intent:
                logger.debug("  ℹ️ No specific intent matched, using general_query")
                best_intent = "general_query"
                best_confidence = 0.3
                best_metadata = {"type": "ai"}
            
            logger.info(f"🎯 Routed to: {best_intent} (confidence: {best_confidence:.2f})")
            return best_intent, best_metadata, best_confidence
        
        except Exception as e:
            logger.error(f"❌ Routing error: {e}")
            return "general_query", {"type": "ai"}, 0.0
    
    @staticmethod
    def get_intent_type(intent: str) -> str:
        """Get the type of an intent"""
        return IntentRouter.intents.get(intent, {}).get("type", "unknown")
    
    @staticmethod
    def is_device_action(intent: str) -> bool:
        """Check if intent is a device action"""
        return IntentRouter.get_intent_type(intent) == "device"
    
    @staticmethod
    def is_weather_action(intent: str) -> bool:
        """Check if intent is weather related"""
        return IntentRouter.get_intent_type(intent) == "weather"

# Public routing function
def route(user_input: str) -> Tuple[str, Dict[str, Any], float]:
    """Public API for intent routing"""
    return IntentRouter.route_intent(user_input)