from fastapi import FastAPI, WebSocket
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
import jarvis_ai
import whisper
import base64
import tempfile
import os
import json
import ssl
import uvicorn

app = FastAPI()
app.mount("/client", StaticFiles(directory=".", html=True), name="client")

@app.get("/")
def root():
    return RedirectResponse(url="/client")

model = whisper.load_model("small")

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    print("🔌 Connessione WebSocket aperta")

    session_id = "default"
    connected = True

    async def sender(obj):
        if connected:
            try:
                await ws.send_text(json.dumps(obj))
            except Exception as e:
                print(f"❌ Errore invio WebSocket: {e}")

    try:
        while True:
            try:
                data = await ws.receive_text()
            except Exception as e:
                print(f"⚠️ Connessione interrotta: {e}")
                connected = False
                break

            print("📥 Messaggio ricevuto")

            try:
                msg = json.loads(data)
            except Exception as e:
                print(f"❌ Errore parsing JSON: {e}")
                await sender({"type": "error", "message": "JSON non valido"})
                continue

            mtype = msg.get("type")

            if mtype == "start_session":
                session_id = msg.get("session_id", "default")
                print(f"🧠 Sessione avviata: {session_id}")
                await sender({"type": "info", "message": f"Sessione {session_id} avviata"})
                continue

            elif mtype == "wav":
                b64 = msg.get("wav_base64")
                if not b64:
                    await sender({"type": "error", "message": "Audio mancante"})
                    continue

                try:
                    audio_bytes = base64.b64decode(b64)
                except Exception as e:
                    await sender({"type": "error", "message": "Base64 non valido"})
                    continue

                tmp_fd, tmp_path = tempfile.mkstemp(suffix=".wav")
                os.close(tmp_fd)
                with open(tmp_path, "wb") as f:
                    f.write(audio_bytes)
                print(f"💾 WAV salvato: {tmp_path} ({len(audio_bytes)} bytes)")

                # Trascrizione
                try:
                    result = model.transcribe(tmp_path, language="it")
                    text = result.get("text", "").strip()
                    print(f"🗣️ Trascrizione: {text}")
                    await sender({"type": "transcript", "text": text})
                except Exception as e:
                    print(f"❌ Errore trascrizione: {e}")
                    await sender({"type": "error", "message": f"Errore trascrizione: {e}"})
                    continue
                finally:
                    os.remove(tmp_path)

                # GPT streaming + TTS progressivo
                try:
                    print("🤖 Streaming GPT...")
                    await jarvis_ai.generate_and_stream(session_id, text, sender)
                except Exception as e:
                    print(f"❌ Errore GPT streaming: {e}")
                    await sender({"type": "error", "message": f"Errore GPT: {e}"})
                    continue

            else:
                await sender({"type": "error", "message": "Tipo messaggio non riconosciuto"})

    except Exception as e:
        print(f"⚠️ Errore WebSocket: {e}")
    finally:
        connected = False
        print("🔌 Connessione WebSocket chiusa")

if __name__ == "__main__":
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain("cert.pem", "key.pem")
    uvicorn.run("server_final:app", host="0.0.0.0", port=5000, ssl_keyfile="key.pem", ssl_certfile="cert.pem")
