"""
jarvis_ai.py
- Robust GPT streaming wrapper (compatibile con varianti SDK)
- gestione session histories
- ElevenLabs TTS sync wrapper eseguita in executor (non blocca event loop)
- chunking intelligente per TTS progressivo
- logging dettagliato
"""

import re
import base64
import requests
import config
import asyncio
import traceback
from openai import OpenAI

# Single OpenAI client
client = OpenAI(api_key=config.OPENAI_API_KEY)

# Per sessioni multiple
session_histories = {}

SYSTEM_PROMPT = "Sei Jarvis, l'assistente AI personale di Matteo. Elegante, preciso, conciso, con tono neutro e professionale."

# ----------------- utils -----------------
def get_history(session_id):
    return session_histories.setdefault(session_id, [])

def log(msg):
    print(f"[JarvisAI] {msg}")

# ----------------- chunker -----------------
def chunk_text_for_tts(text, max_chars=400, min_chars=80):
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    chunks = []
    cur = ""
    for s in sentences:
        if not s:
            continue
        if len(cur) + len(s) < max_chars:
            cur = (cur + " " + s).strip()
        else:
            if len(cur) >= min_chars:
                chunks.append(cur)
                cur = s
            else:
                cur = (cur + " " + s).strip()
                chunks.append(cur)
                cur = ""
    if cur:
        chunks.append(cur)
    # merge too-short trailing chunks
    out = []
    i = 0
    while i < len(chunks):
        c = chunks[i]
        if len(c) < min_chars and i + 1 < len(chunks):
            c = c + " " + chunks[i+1]
            i += 1
        out.append(c.strip())
        i += 1
    return out

# ----------------- ElevenLabs TTS -----------------
def elevenlabs_tts_get_audio_bytes(text):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{config.ELEVENLABS_VOICE_ID}"
    headers = {"xi-api-key": config.ELEVENLABS_API_KEY, "Content-Type": "application/json"}
    data = {"text": text, "voice_settings": {"stability": 0.6, "similarity_boost": 0.7}}
    r = requests.post(url, headers=headers, json=data, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"ElevenLabs TTS failed {r.status_code}: {r.text}")
    return r.content

def speak(text, return_base64=False):
    b = elevenlabs_tts_get_audio_bytes(text)
    if return_base64:
        return base64.b64encode(b).decode()
    return b

# ----------------- sync ask fallback -----------------
def ask_gpt(text):
    """Synchronous non-streaming fallback"""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": text}
    ]
    log("ask_gpt called (sync fallback)")
    resp = client.chat.completions.create(
        model=config.OPENAI_MODEL,
        messages=messages,
        temperature=0.2,
        max_tokens=800
    )
    try:
        return resp.choices[0].message.content
    except Exception:
        # fallback shape
        return getattr(resp.choices[0], "text", str(resp))

# ----------------- streaming helper (robusto) -----------------
async def stream_gpt_messages(messages):
    """
    Async generator wrapper for OpenAI streaming.
    Yields dictionaries: {"type":"delta","content":str} or {"type":"done","content":full}
    Falls back to single response if streaming unsupported.
    """
    full = ""
    try:
        # Some SDKs expose 'chat.completions.stream' as coroutine returning async generator
        # Others may require client.chat.completions.stream(...) without await; handle both.
        try:
            stream_or_agen = await client.chat.completions.stream(
                model=config.OPENAI_MODEL,
                messages=messages,
                temperature=0.2,
                max_tokens=800
            )
        except TypeError:
            # maybe the method is not awaitable and returns an async generator directly
            stream_or_agen = client.chat.completions.stream(
                model=config.OPENAI_MODEL,
                messages=messages,
                temperature=0.2,
                max_tokens=800
            )

        # If stream_or_agen is not async iterable, fallback to sync response
        if not hasattr(stream_or_agen, "__aiter__"):
            log("streaming not available, using sync fallback")
            final = ask_gpt(messages[-1]["content"] if messages else "")
            yield {"type": "done", "content": final}
            return

        async for part in stream_or_agen:
            # robust extraction of token text across SDK shapes
            delta = None
            try:
                # new SDK object-like shapes
                if hasattr(part, "choices"):
                    ch = part.choices[0]
                    # delta as attribute or dict
                    if hasattr(ch, "delta"):
                        d = ch.delta
                        # try attribute content
                        if hasattr(d, "content"):
                            delta = d.content
                        elif isinstance(d, dict):
                            delta = d.get("content")
                    # some server messages may carry "text" directly
                    if delta is None and hasattr(ch, "text"):
                        delta = ch.text
                elif isinstance(part, dict):
                    # older dict shapes
                    delta = part.get("choices", [{}])[0].get("delta", {}).get("content")
                    if delta is None:
                        # fallback to choices[0].text
                        delta = part.get("choices", [{}])[0].get("text")
            except Exception:
                # ignore parsing error for this part
                delta = None

            if delta:
                full += delta
                yield {"type": "delta", "content": delta}
        yield {"type": "done", "content": full}
    except Exception as e:
        # complete error trace for server logs
        tb = traceback.format_exc()
        log(f"stream_gpt_messages exception: {e}\n{tb}")
        # fallback: attempt sync completion
        try:
            final = ask_gpt(messages[-1]["content"] if messages else "")
            yield {"type": "done", "content": final}
        except Exception as e2:
            yield {"type": "error", "content": f"{e} | fallback error: {e2}"}

# ----------------- high level: generate_and_stream -----------------
async def generate_and_stream(session_id, user_text, ws_send):
    """
    session_id: id for chat history
    user_text: text from transcription
    ws_send: async callable to send JSON to client, e.g. await ws_send(dict)
    Behavior:
      - append user message to history
      - stream tokens from GPT, forward partial_text messages
      - when buffer past thresholds, create TTS chunk for first available sentence and send audio_chunk
      - on done, append assistant history and send done
    """
    try:
        history = get_history(session_id)
        history.append({"role": "user", "content": user_text})
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history

        # track how many characters already sent to TTS
        partial_buffer = ""
        tts_sent_up_to = 0

        # small safety timer to flush periodically (in seconds)
        last_delta_ts = asyncio.get_event_loop().time()
        FLUSH_INTERVAL = 10.0

        async for ev in stream_gpt_messages(messages):
            if ev.get("type") == "delta":
                delta = ev.get("content", "")
                partial_buffer += delta
                # forward partial immediately
                try:
                    await ws_send({"type": "partial_text", "delta": delta, "full": partial_buffer})
                except Exception as e:
                    log(f"ws_send error while sending partial_text: {e}")

                # attempt to produce TTS for newly available content
                remaining = partial_buffer[tts_sent_up_to:].strip()
                # only act if some content and we haven't TTSed it
                if len(remaining) >= 40:
                    # make chunks from remaining
                    chunks = chunk_text_for_tts(remaining, max_chars=350, min_chars=40)
                    if chunks:
                        first = chunks[0]
                        # ensure we don't overlap sending same text twice
                        tts_sent_up_to += len(first)
                        # call ElevenLabs in executor to avoid blocking
                        loop = asyncio.get_event_loop()
                        try:
                            audio_bytes = await loop.run_in_executor(None, elevenlabs_tts_get_audio_bytes, first)
                            b64 = base64.b64encode(audio_bytes).decode()
                            try:
                                await ws_send({"type": "audio_chunk", "text_chunk": first, "audio_b64": b64})
                            except Exception as e:
                                log(f"ws_send error while sending audio_chunk: {e}")
                        except Exception as e:
                            log(f"ElevenLabs TTS error for chunk: {e}")
                            try:
                                await ws_send({"type": "error", "message": f"TTS failed: {e}"})
                            except Exception:
                                pass
                last_delta_ts = asyncio.get_event_loop().time()

            elif ev.get("type") == "done":
                final = ev.get("content", "")
                # append assistant to history
                history.append({"role": "assistant", "content": final})
                try:
                    await ws_send({"type": "done", "full": final})
                except Exception as e:
                    log(f"ws_send error while sending done: {e}")
                return

            elif ev.get("type") == "error":
                # forward error to client
                try:
                    await ws_send({"type": "error", "message": ev.get("content")})
                except Exception:
                    pass
                return

        # if generator completes without done event
        if partial_buffer:
            history.append({"role": "assistant", "content": partial_buffer})
            try:
                await ws_send({"type": "done", "full": partial_buffer})
            except Exception as e:
                log(f"ws_send error final: {e}")
    except Exception as e:
        tb = traceback.format_exc()
        log(f"generate_and_stream top-level exception: {e}\n{tb}")
        try:
            await ws_send({"type": "error", "message": f"Internal error: {e}"})
        except Exception:
            pass
