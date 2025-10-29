"""config - Configurazione JARVIS centralizzata"""

import os
from pathlib import Path

# Carica .env se esiste
try:
    from dotenv import load_dotenv
    env_file = Path(__file__).parent.parent / '.env'
    if env_file.exists():
        load_dotenv(env_file)
except ImportError:
    pass

# ============================================================================
# CORE - LLM & AI
# ============================================================================

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

if not OPENAI_API_KEY:
    print("⚠️  OPENAI_API_KEY non configurata!")
    print("   Imposta: export OPENAI_API_KEY='sk-proj-xxx'")

# ============================================================================
# SERVER - WEB
# ============================================================================

HOST = os.environ.get("JARVIS_HOST", "0.0.0.0")
PORT = int(os.environ.get("JARVIS_PORT", "5000"))
USE_HTTPS = os.environ.get("JARVIS_USE_HTTPS", "0") != "0"

# ============================================================================
# AUDIO - TTS
# ============================================================================

EDGE_TTS_VOICE = os.environ.get("EDGE_TTS_VOICE", "it-IT-DiegoNeural")
EDGE_TTS_RATE = os.environ.get("EDGE_TTS_RATE", "+0%")
EDGE_TTS_PITCH = os.environ.get("EDGE_TTS_PITCH", "-12Hz")

# ============================================================================
# DEBUG
# ============================================================================

VERBOSE = os.environ.get("JARVIS_VERBOSE", "0") == "1"

# ============================================================================
# SERVICES
# ============================================================================

SERVICES_ENABLED = {
    "weather": True,
    "email": False,
    "calendar": False,
    "smart_home": False
}

# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
    "HOST",
    "PORT",
    "USE_HTTPS",
    "EDGE_TTS_VOICE",
    "EDGE_TTS_RATE",
    "EDGE_TTS_PITCH",
    "VERBOSE",
    "SERVICES_ENABLED"
]
