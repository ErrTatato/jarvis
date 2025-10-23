import asyncio
import json
import numpy as np
from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack
from aiortc.contrib.media import MediaBlackhole
from av import AudioFrame
import requests
from pydub import AudioSegment
import io
import config
from openai import OpenAI
import traceback
from pathlib import Path
import os

# ==== Config / client LLM ====
client = OpenAI(api_key=config.OPENAI_API_KEY)

async def llm_stream_or_simulate(prompt):
    full = ""
    try:
        stream = client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {"role":"system","content":"Sei Jarvis: elegante, preciso, conciso, neutro e professionale."},
                {"role":"user","content":prompt}
            ],
            temperature=0.2,
            max_tokens=400,
            stream=True
        )
        for part in stream:
            delta = None
            try:
                delta = part.choices[0].delta.content
            except Exception:
                delta = None
            if delta:
                full += delta
                yield ("delta", delta)
        yield ("done", full)
        return
    except Exception:
        pass
    # fallback sync + simulated streaming
    try:
        resp = client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {"role":"system","content":"Sei Jarvis: elegante, preciso, conciso, neutro e professionale."},
                {"role":"user","content":prompt}
            ],
            temperature=0.2,
            max_tokens=400
        )
        text = resp.choices[0].message.content
    except Exception:
        text = "Non riesco a rispondere al momento."
    for chunk in text.split(". "):
        yield ("delta", chunk + (". " if not chunk.endswith(".") else ""))
        await asyncio.sleep(0.05)
    yield ("done", text)

# ==== TTS (ElevenLabs -> MP3 -> PCM int16) ====
def elevenlabs_tts_mp3(text):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{config.ELEVENLABS_VOICE_ID}"
    headers = {"xi-api-key": config.ELEVENLABS_API_KEY, "Content-Type": "application/json"}
    data = {"text": text, "voice_settings": {"stability": 0.6, "similarity_boost": 0.7}}
    r = requests.post(url, headers=headers, json=data, timeout=25)
    if r.status_code != 200:
        raise RuntimeError(f"ElevenLabs TTS failed {r.status_code}: {r.text}")
    return r.content

def mp3_to_int16_pcm(mp3_bytes, target_rate=48000):
    audio = AudioSegment.from_file(io.BytesIO(mp3_bytes), format="mp3")
    audio = audio.set_channels(1).set_frame_rate(target_rate).set_sample_width(2)
    return np.frombuffer(audio.raw_data, dtype=np.int16)

# ==== WebRTC Out Track ====
class SynthTrack(MediaStreamTrack):
    kind = "audio"
    def __init__(self):
        super().__init__() 
        self._sample_rate = 48000
        self._hop = int(self._sample_rate * 0.02)
        self._queue = asyncio.Queue()
        self._silence = np.zeros((self._hop,), dtype=np.int16)

    async def push_pcm_int16(self, pcm_int16):
        hop = self._hop
        for i in range(0, len(pcm_int16), hop):
            await self._queue.put(pcm_int16[i:i+hop])

    async def recv(self):
        try:
            chunk = await asyncio.wait_for(self._queue.get(), timeout=0.04)
        except asyncio.TimeoutError:
            chunk = self._silence
        frame = AudioFrame(format="s16", layout="mono", samples=len(chunk))
        mv = memoryview(frame.planes[0].buffer).cast("h")
        mv[:] = chunk
        frame.sample_rate = self._sample_rate
        try:
            self._queue.task_done()
        except Exception:
            pass
        return frame

# ==== Inbound Track ====
class InboundAudioTrack(MediaStreamTrack):
    kind = "audio"
    def __init__(self, track, on_pcm):
        super().__init__()
        self._track = track
        self._on_pcm = on_pcm

    async def recv(self):
        frame = await self._track.recv()
        arr = frame.to_ndarray()
        pcm = arr[0] if arr.ndim > 1 else arr
        if pcm.dtype == np.float32:
            pcm = (np.clip(pcm, -1.0, 1.0) * 32767.0).astype(np.int16)
        else:
            pcm = pcm.astype(np.int16)
        if self._on_pcm:
            try:
                self._on_pcm(pcm)
            except Exception:
                pass
        return frame

# ==== Vosk STT (singleton loader, robust) ====
_VOSK_MODEL_SINGLETON = {"model": None, "path": None}

class VoskStreamer:
    def __init__(self, model_path):
        self.model = None
        self.rec = None
        self.partial_queue = asyncio.Queue()
        self.final_queue = asyncio.Queue()
        self._last_partial = ""

        if not model_path:
            print("[STT] No model_path provided")
            return

        p = Path(model_path).expanduser().resolve()
        if not p.exists() or not p.is_dir():
            print(f"[STT] VOSK model path non valido: {p}")
            return

        # load singleton model if not loaded or path changed
        if _VOSK_MODEL_SINGLETON["model"] is None or _VOSK_MODEL_SINGLETON["path"] != str(p):
            try:
                from vosk import Model
                print(f"[STT] Caricamento Vosk model da: {p}")
                _VOSK_MODEL_SINGLETON["model"] = Model(str(p))
                _VOSK_MODEL_SINGLETON["path"] = str(p)
                print("[STT] Modello Vosk caricato (singleton).")
            except Exception as e:
                print(f"[STT] ERRORE caricamento Vosk model: {e}")
                _VOSK_MODEL_SINGLETON["model"] = None
                _VOSK_MODEL_SINGLETON["path"] = None

        if _VOSK_MODEL_SINGLETON["model"] is None:
            return

        try:
            from vosk import KaldiRecognizer
            self.model = _VOSK_MODEL_SINGLETON["model"]
            self.rec = KaldiRecognizer(self.model, 48000)
            self.rec.SetWords(True)
            print("[STT] Recognizer pronto.")
        except Exception as e:
            print(f"[STT] ERRORE inizializzazione recognizer: {e}")
            self.rec = None

    def feed_pcm(self, pcm_int16):
        if self.rec is None:
            return
        data = pcm_int16.tobytes()
        try:
            if self.rec.AcceptWaveform(data):
                res = json.loads(self.rec.Result())
                text = res.get("text", "").strip()
                if text:
                    asyncio.create_task(self.final_queue.put(text))
            else:
                res = json.loads(self.rec.PartialResult())
                p = res.get("partial", "").strip()
                if p and p != self._last_partial:
                    self._last_partial = p
                    asyncio.create_task(self.partial_queue.put(p))
        except Exception:
            # ignore Vosk transient errors
            pass

    async def get_final(self):
        return await self.final_queue.get()

    async def iter_partials(self):
        while True:
            t = await self.partial_queue.get()
            yield t

# ==== Web app + routes ====
pcs = set()
app = web.Application()

# serve homepage index.html (client)
BASE_DIR = Path(__file__).parent
async def client_page(request):
    f = BASE_DIR / "index.html"
    if f.exists():
        return web.FileResponse(str(f))
    return web.Response(text="index.html not found", status=404)

app.router.add_get("/", client_page)

async def offer(request):
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
    pc = RTCPeerConnection()
    pcs.add(pc)
    print("Peer created")

    synth_out = SynthTrack()
    stt = VoskStreamer(model_path=getattr(config, "VOSK_MODEL_PATH", None))
    pc.addTrack(synth_out)

    # DataChannel for transcripts/deltas
    server_dc = pc.createDataChannel("server")

    @pc.on("track")
    def on_track(track):
        if track.kind == "audio":
            inbound = InboundAudioTrack(track, stt.feed_pcm)
            asyncio.ensure_future(MediaBlackhole().consume(inbound))

            # if STT not available, notify client and run fallback notice
            if stt.rec is None:
                try:
                    server_dc.send(json.dumps({
                        "type": "error",
                        "message": "STT non disponibile. Controlla config.VOSK_MODEL_PATH."
                    }))
                except Exception:
                    pass

                async def fallback_notice():
                    text = "Trascrizione non disponibile. Controlla configurazione modello Vosk."
                    loop = asyncio.get_event_loop()
                    try:
                        mp3 = await loop.run_in_executor(None, elevenlabs_tts_mp3, text)
                        pcm = await loop.run_in_executor(None, mp3_to_int16_pcm, mp3)
                        await synth_out.push_pcm_int16(pcm)
                    except Exception as e:
                        print("Fallback TTS error:", e)
                asyncio.create_task(fallback_notice())
                return

            async def stt_partials_loop():
                async for p in stt.iter_partials():
                    try:
                        server_dc.send(json.dumps({"type":"stt_partial","text":p}))
                    except Exception:
                        pass

            async def pipeline_loop():
                while True:
                    final_text = await stt.get_final()
                    try:
                        server_dc.send(json.dumps({"type":"stt_final","text":final_text}))
                    except Exception:
                        pass

                    async for kind, payload in llm_stream_or_simulate(final_text):
                        if kind == "delta":
                            try:
                                server_dc.send(json.dumps({"type":"llm_delta","text":payload}))
                            except Exception:
                                pass
                            try:
                                loop = asyncio.get_event_loop()
                                mp3 = await loop.run_in_executor(None, elevenlabs_tts_mp3, payload)
                                pcm = await loop.run_in_executor(None, mp3_to_int16_pcm, mp3)
                                await synth_out.push_pcm_int16(pcm)
                            except Exception as e:
                                try:
                                    server_dc.send(json.dumps({"type":"error","message":str(e)}))
                                except Exception:
                                    pass
            # start tasks
            asyncio.create_task(stt_partials_loop())
            asyncio.create_task(pipeline_loop())

    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    return web.json_response({"sdp": pc.localDescription.sdp, "type": pc.localDescription.type})

async def on_shutdown(app):
    await asyncio.gather(*[pc.close() for pc in pcs], return_exceptions=True)
    pcs.clear()

app.on_shutdown.append(on_shutdown)
app.router.add_post("/offer", offer)

# ==== Avvio HTTPS (web.run_app con ssl_context) ====
def verify_vosk_path_print():
    p = getattr(config, "VOSK_MODEL_PATH", None)
    if not p:
        print("[STT] ATTENZIONE: config.VOSK_MODEL_PATH non impostato")
        return
    try:
        pth = Path(p).resolve()
        if not pth.exists():
            print(f"[STT] ATTENZIONE: VOSK_MODEL_PATH non esiste: {pth}")
            return
        print(f"[STT] VOSK_MODEL_PATH verificato: {pth}")
        # debug listing (mostra poche entries)
        try:
            entries = [e.name for e in pth.iterdir()][:20]
            print("[STT] sample content:", entries)
        except Exception:
            pass
    except Exception:
        pass

if __name__ == "__main__":
    verify_vosk_path_print()
    import ssl
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    # expects cert.pem and key.pem present in same folder
    cert_file = Path("cert.pem")
    key_file = Path("key.pem")
    if not cert_file.exists() or not key_file.exists():
        print("[SSL] cert.pem or key.pem not found in folder, starting without SSL is not recommended.")
        # you may still run without ssl by using web.run_app without ssl_context
    else:
        ssl_context.load_cert_chain(str(cert_file), str(key_file))
    web.run_app(app, host="0.0.0.0", port=5000, ssl_context=ssl_context)
