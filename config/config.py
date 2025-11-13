import os
from pathlib import Path

# ===== DIRECTORIES =====
BASE_DIR = Path(__file__).parent.parent
UI_DIR = BASE_DIR / "ui"
SERVICES_DIR = BASE_DIR / "services"
CONFIG_DIR = BASE_DIR / "config"
CERTS_DIR = BASE_DIR / "certs"

# ===== API KEYS =====
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY", "demo")

# ===== SERVER =====
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 5000
SSL_ENABLED = CERTS_DIR.exists() and (CERTS_DIR / "cert.pem").exists()

# ===== MODELS =====
CHAT_MODEL = "gpt-4o-mini"
TTS_MODEL = "tts-1-hd"
STT_MODEL = "whisper-1"

# ===== TTS =====
TTS_VOICE = "onyx"
TTS_LANGUAGE = "it-IT"

# ===== PROMPTS =====
SYSTEM_PROMPT = """Sei JARVIS, il maggiordomo intelligente di Tony Stark.
Tono sofisticato, elegante, sarcastico, italiano.
Risposte BREVI (max 30 parole). 100% ITALIANO PURO."""

# ===== LOGGING =====
LOG_FORMAT = '[%(asctime)s] %(levelname)s: %(message)s'
LOG_DATE_FORMAT = '%H:%M:%S'
LOG_LEVEL = "INFO"