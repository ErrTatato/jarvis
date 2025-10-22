from flask import Flask, request, jsonify, send_from_directory
import os
import tempfile
import base64
import jarvis_ai
import ssl
import traceback
import logging
from datetime import datetime

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler("error.log"), logging.StreamHandler()]
)

MIN_WAV_BYTES = 2000  # minimal reasonable WAV header+data size

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/client")
def client():
    return send_from_directory(".", "index.html")

@app.route("/status")
def status():
    return jsonify({"status":"ok", "time": datetime.utcnow().isoformat() + "Z"})

@app.route("/ask", methods=["POST"])
def ask():
    tmp_wav_path = None
    try:
        data = request.get_json()
        if not data:
            logging.warning("Richiesta /ask vuota")
            return jsonify({"error":"Richiesta vuota"}), 400

        # Support either wav_base64 (new client) or legacy audio_base64 (not recommended)
        if "wav_base64" in data:
            b64 = data["wav_base64"]
            try:
                wav_bytes = base64.b64decode(b64)
            except Exception as e:
                logging.error(f"Base64 decode fallito: {e}")
                return jsonify({"error":"Base64 non valido"}), 400

            # basic size check
            if len(wav_bytes) < MIN_WAV_BYTES:
                logging.warning(f"WAV troppo piccolo: {len(wav_bytes)} bytes")
                return jsonify({"error":"WAV troppo piccolo o corrotto", "size": len(wav_bytes)}), 400

            tmp_fd, tmp_wav_path = tempfile.mkstemp(suffix=".wav")
            os.close(tmp_fd)
            with open(tmp_wav_path, "wb") as f:
                f.write(wav_bytes)
            logging.info(f"Salvato WAV temporaneo: {tmp_wav_path} ({len(wav_bytes)} bytes)")

        elif "audio_base64" in data:
            # backward compatibility but prefer wav_base64
            b64 = data["audio_base64"]
            try:
                webm_bytes = base64.b64decode(b64)
            except Exception as e:
                logging.error(f"Base64 decode fallito: {e}")
                return jsonify({"error":"Base64 non valido"}), 400
            tmp_fd, tmp_webm = tempfile.mkstemp(suffix=".webm")
            os.close(tmp_fd)
            with open(tmp_webm, "wb") as f:
                f.write(webm_bytes)
            size = os.path.getsize(tmp_webm)
            logging.info(f"Ricevuto webm temporaneo (legacy): {tmp_webm} ({size} bytes)")
            if size < 3000:
                return jsonify({"error":"Webm troppo piccolo, invia WAV o chunk più lunghi", "size": size}), 400
            # try convert webm -> wav with ffmpeg; fallback error handled
            tmp_fd, tmp_wav_path = tempfile.mkstemp(suffix=".wav")
            os.close(tmp_fd)
            try:
                subprocess.run([
                    "ffmpeg", "-y", "-i", tmp_webm, "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", tmp_wav_path
                ], check=True, capture_output=True)
                logging.info(f"Converted legacy webm to wav: {tmp_wav_path}")
            except Exception as e:
                err = getattr(e, "stderr", str(e))
                logging.error(f"ffmpeg conversion failed: {err}")
                return jsonify({"error":"Conversione webm->wav fallita", "detail": str(err)}), 500
            finally:
                try: os.remove(tmp_webm)
                except Exception: pass

        else:
            logging.warning("Nessuna chiave audio trovata nella richiesta")
            return jsonify({"error":"Nessun audio inviato (usa wav_base64)"}), 400

        # Transcribe with Whisper (jarvis_ai.transcribe_audio_chunk expects file path)
        try:
            text = jarvis_ai.transcribe_audio_chunk(tmp_wav_path)
            logging.info(f"Trascrizione: {text!r}")
        except Exception as e:
            tb = traceback.format_exc()
            logging.error(f"Errore trascrizione: {e}\n{tb}")
            return jsonify({"error":"Errore trascrizione", "detail": str(e), "traceback": tb}), 500

        if not text:
            logging.warning("Trascrizione vuota")
            return jsonify({"error":"Trascrizione vuota"}), 400

        # GPT generation
        try:
            gpt_response = jarvis_ai.ask_gpt(text)
            logging.info(f"GPT risposta: {gpt_response!r}")
        except Exception as e:
            tb = traceback.format_exc()
            logging.error(f"Errore GPT: {e}\n{tb}")
            return jsonify({"error":"Errore generazione GPT", "detail": str(e), "traceback": tb}), 500

        # TTS
        try:
            audio_base64 = jarvis_ai.speak(gpt_response, return_base64=True)
        except Exception as e:
            tb = traceback.format_exc()
            logging.error(f"Errore TTS: {e}\n{tb}")
            return jsonify({"error":"Errore sintesi vocale", "detail": str(e), "traceback": tb}), 500

        return jsonify({"text": text, "gpt": gpt_response, "audio_base64": audio_base64})

    except Exception as e:
        tb = traceback.format_exc()
        logging.error(f"Errore imprevisto /ask: {e}\n{tb}")
        return jsonify({"error":"Errore interno server", "detail": str(e), "traceback": tb}), 500

    finally:
        try:
            if tmp_wav_path and os.path.exists(tmp_wav_path):
                os.remove(tmp_wav_path)
        except Exception:
            pass

@app.route("/wake", methods=["POST"])
def wake():
    logging.info("Trigger vocale ricevuto: 'Hey Jarvis'")
    return jsonify({"status":"Jarvis attivato"})

if __name__ == "__main__":
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile="cert.pem", keyfile="key.pem")
    app.run(host="0.0.0.0", port=5000, ssl_context=context, debug=True)
