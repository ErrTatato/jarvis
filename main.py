#!/usr/bin/env python3
"""
main.py - Entry point JARVIS
Esegui con: python main.py
"""

import sys
import os
from server.server_webrtc import app, web
from config.config import HOST, PORT, USE_HTTPS
import ssl
from pathlib import Path

if __name__ == "__main__":
    print("=" * 80)
    print("🤖 JARVIS - Starting...")
    print("=" * 80)
    
    ssl_context = None
    if USE_HTTPS:
        cert_file = Path("certs/cert.pem")
        key_file = Path("certs/key.pem")
        if cert_file.exists() and key_file.exists():
            try:
                ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                ssl_context.load_cert_chain(str(cert_file), str(key_file))
                print("[SSL] ✅ HTTPS enabled")
            except Exception as e:
                print(f"[SSL] ❌ {e}")
    
    print(f"[SERVER] Running on {HOST}:{PORT}")
    web.run_app(app, host=HOST, port=PORT, ssl_context=ssl_context)
