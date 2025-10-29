import os
from dotenv import load_dotenv
load_dotenv()  # Carica da .env


# ============================================================================
# API KEYS
# ============================================================================
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# ============================================================================
# MODELLI
# ============================================================================
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

# ============================================================================
# TTS - Edge ottimizzato per JARVIS
# ============================================================================

# Voce italiana (DiegoNeural è la migliore per JARVIS)
EDGE_TTS_VOICE = os.environ.get("EDGE_TTS_VOICE", "it-IT-DiegoNeural")

# Velocità: +0% = normale (JARVIS non ha fretta!)
EDGE_TTS_RATE = os.environ.get("EDGE_TTS_RATE", "+0%")

# Pitch: -12Hz = molto profondo (voce autorevole tipo JARVIS)
EDGE_TTS_PITCH = os.environ.get("EDGE_TTS_PITCH", "-12Hz")

# ============================================================================
# AUDIO
# ============================================================================
TARGET_SR = int(os.environ.get("TARGET_SR", "24000"))
CHUNK_MS = int(os.environ.get("CHUNK_MS", "100"))

# ============================================================================
# SERVER
# ============================================================================
HOST = os.environ.get("JARVIS_HOST", "0.0.0.0")
PORT = int(os.environ.get("JARVIS_PORT", "5000"))
USE_HTTPS = os.environ.get("JARVIS_USE_HTTPS", "1") != "0"

# ============================================================================
# LOGGING
# ============================================================================
VERBOSE = os.environ.get("JARVIS_VERBOSE", "0") == "1"

# ============================================================================
# TTS SETTINGS
# ============================================================================
TTS_MAX_CONCURRENT = int(os.environ.get("TTS_MAX_CONCURRENT", "3"))
TTS_RETRY_COUNT = int(os.environ.get("TTS_RETRY_COUNT", "2"))
TTS_RETRY_BACKOFF = float(os.environ.get("TTS_RETRY_BACKOFF", "1.5"))

# ============================================================================
# SSL
# ============================================================================
VERIFY_SSL = os.environ.get("JARVIS_VERIFY_SSL", "1") == "1"

# ============================================================================
# WAKE WORD
# ============================================================================
WAKE_PATH = os.environ.get("WAKE_PATH", "/wake")
