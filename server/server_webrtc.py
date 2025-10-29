#!/usr/bin/env python3
"""
server_webrtc.py - JARVIS OPZIONE C (Streaming Sequenziale)
"""
import asyncio
import json
import os
import tempfile
import traceback
import base64
from pathlib import Path
import numpy as np
from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack
from av import AudioFrame
import config
from core.speak_edge import speak_edge
from core.jarvis_ai import llm_stream

DEBUG = getattr(config, "VERBOSE", False)

def log_tag(tag, *parts):
    if not DEBUG:
        if tag not in ("USER", "GPT", "SSL", "PC", "WHISPER", "DC", "TTS"):
            return
    try:
        print(f"[{tag}]", *parts)
    except Exception:
        pass

class SynthTrack(MediaStreamTrack):
    kind = "audio"
    def __init__(self):
        super().__init__()
        self._queue = asyncio.Queue()
    async def recv(self):
        await asyncio.sleep(1)
        return AudioFrame.from_ndarray(np.zeros((160, 1), dtype=np.int16), format="s16", layout="mono")

active_connections = {}
pcs = set()
app = web.Application()
BASE_DIR = Path(__file__).parent

async def client_page(request):
    f = BASE_DIR / "index.html"
    if f.exists():
        return web.FileResponse(str(f))
    return web.Response(text="index.html not found", status=404)

app.router.add_get("/", client_page)

async def transcribe_audio(request):
    try:
        reader = await request.multipart()
        audio_data = None
        async for field in reader:
            if field.name == 'audio':
                audio_data = await field.read()
                break
        if not audio_data:
            return web.json_response({"error": "No audio"}, status=400)
        
        log_tag("WHISPER", f"Ricevuti {len(audio_data)} bytes")
        with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as tmp:
            tmp.write(audio_data)
            tmp_path = tmp.name
        
        try:
            from openai import OpenAI
            client = OpenAI(api_key=getattr(config, "OPENAI_API_KEY", None))
            with open(tmp_path, 'rb') as audio_file:
                transcription = client.audio.transcriptions.create(
                    model="whisper-1", file=audio_file, language="it", temperature=0.0
                )
            text = transcription.text.strip()
            log_tag("WHISPER", f"✅ '{text}'")
            return web.json_response({"text": text})
        finally:
            try:
                os.remove(tmp_path)
            except:
                pass
    except Exception as e:
        log_tag("WHISPER", f"❌ {e}")
        return web.json_response({"error": str(e)}, status=500)

app.router.add_post("/transcribe", transcribe_audio)

TTS_SEM = asyncio.Semaphore(3)

async def offer(request):
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
    pc = RTCPeerConnection()
    pcs.add(pc)
    pc_id = id(pc)
    log_tag("PC", f"Peer: {pc_id}")
    synth_out = SynthTrack()
    
    @pc.on("datachannel")
    def on_datachannel(channel):
        active_connections[pc_id] = channel
        log_tag("DC", "✅ Channel")
        
        @channel.on("open")
        def on_open():
            greeting = "Come posso esserle utile, signore?"
            channel.send(json.dumps({"type":"llm_fragment","text":greeting}))
            asyncio.create_task(send_audio_chunk(channel, greeting, is_final=True))
        
        @channel.on("close")
        def on_close():
            if pc_id in active_connections:
                del active_connections[pc_id]
        
        @channel.on("message")
        def on_message(message):
            try:
                obj = json.loads(message)
            except:
                return
            
            if obj and obj.get("type") == "client_ready":
                channel.send(json.dumps({"type":"ack"}))
            elif obj and obj.get("type") == "user_question":
                question = obj.get("text", "").strip()
                if question:
                    asyncio.create_task(process_question(question, pc_id))
    
    @pc.on("track")
    def on_track(track):
        pass
    
    async def process_question(question, conn_id):
        """OPZIONE C - Streaming a frasi + riproduzione sequenziale"""
        log_tag("USER", question)
        dc = active_connections.get(conn_id)
        if not dc:
            return
        
        dc.send(json.dumps({"type": "stt_final", "text": question}))
        
        full_text = ""
        sentence_buffer = ""
        chunk_count = 0
        
        async for kind, payload in llm_stream(question):
            if kind == "delta":
                full_text += payload
                sentence_buffer += payload
                dc.send(json.dumps({"type": "llm_delta", "text": payload}))
                
                # Genera TTS a frasi
                if payload in '.!?':
                    sent = sentence_buffer.strip()
                    if sent and len(sent) > 3:
                        chunk_count += 1
                        log_tag("TTS", f"Chunk {chunk_count}: '{sent[:40]}...'")
                        asyncio.create_task(send_audio_chunk(dc, sent, is_final=False))
                    sentence_buffer = ""
                    
            elif kind == "done":
                if full_text:
                    dc.send(json.dumps({"type": "llm_fragment", "text": full_text}))
                    log_tag("GPT", full_text)
                    
                    if sentence_buffer.strip():
                        chunk_count += 1
                        asyncio.create_task(send_audio_chunk(dc, sentence_buffer.strip(), is_final=True))
                    else:
                        dc.send(json.dumps({"type": "audio_stream_end"}))
                
                full_text = ""
    
    async def send_audio_chunk(channel, text, is_final=False):
        """Invia chunk audio con metadata"""
        try:
            await TTS_SEM.acquire()
        except:
            return
        
        try:
            log_tag("TTS", f"Generazione...")
            mp3_bytes = await asyncio.get_running_loop().run_in_executor(
                None, speak_edge, text, None, True, None
            )
            mp3_b64 = base64.b64encode(mp3_bytes).decode('utf-8')
            channel.send(json.dumps({
                "type": "audio_chunk",
                "data": mp3_b64,
                "is_final": is_final
            }))
            log_tag("TTS", f"✅ Chunk ({len(mp3_bytes)} bytes)")
        except Exception as e:
            log_tag("TTS", f"❌ {e}")
            traceback.print_exc()
        finally:
            TTS_SEM.release()
    
    pc.addTrack(synth_out)
    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    return web.json_response({"sdp": pc.localDescription.sdp, "type": pc.localDescription.type})

app.router.add_post("/offer", offer)

async def on_shutdown(app):
    await asyncio.gather(*[pc.close() for pc in pcs], return_exceptions=True)
    pcs.clear()
    active_connections.clear()

app.on_shutdown.append(on_shutdown)

if __name__ == "__main__":
    import ssl
    ssl_context = None
    cert_file = Path("cert.pem")
    key_file = Path("key.pem")
    if cert_file.exists() and key_file.exists():
        try:
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ssl_context.load_cert_chain(str(cert_file), str(key_file))
            log_tag("SSL", "✅ HTTPS")
        except:
            pass
    
    print("=" * 80)
    print("🤖 JARVIS - OPZIONE C (Streaming Sequenziale)")
    print("=" * 80)
    print(f"Host: {config.HOST}:{config.PORT}")
    print(f"TTS: Edge - voce '{config.EDGE_TTS_VOICE}'")
    print("=" * 80)
    
    web.run_app(app, host=config.HOST, port=config.PORT, ssl_context=ssl_context)
