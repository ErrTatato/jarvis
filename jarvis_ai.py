import re
import base64
import requests
import config
import asyncio
import traceback
from openai import OpenAI

client = OpenAI(api_key=config.OPENAI_API_KEY)
session_histories = {}

SYSTEM_PROMPT = "Sei Jarvis, l'assistente AI personale di Matteo. Elegante, ironico, conciso, con tono neutro e professionale."

def get_history(session_id):
    return session_histories.setdefault(session_id, [])

def log(msg):
    print(f"[JarvisAI] {msg}")

def chunk_text_for_tts(text, max_chars=350, min_chars=40):
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    chunks, cur = [], ""
    for s in sentences:
        if not s: continue
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
    if cur: chunks.append(cur)
    out, i = [], 0
    while i < len(chunks):
        c = chunks[i]
        if len(c) < min_chars and i + 1 < len(chunks):
            c = c + " " + chunks[i+1]
            i += 1
        out.append(c.strip())
        i += 1
    return out

def elevenlabs_tts_get_audio_bytes(text):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{config.ELEVENLABS_VOICE_ID}"
    headers = {"xi-api-key": config.ELEVENLABS_API_KEY, "Content-Type": "application/json"}
    data = {"text": text, "voice_settings": {"stability": 0.6, "similarity_boost": 0.7}}
    r = requests.post(url, headers=headers, json=data, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"ElevenLabs TTS failed {r.status_code}: {r.text}")
    return r.content

def ask_gpt(text):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": text}]
    log("ask_gpt called (sync fallback)")
    resp = client.chat.completions.create(
        model=config.OPENAI_MODEL,
        messages=messages,
        temperature=0.2,
        max_tokens=400
    )
    try:
        return resp.choices[0].message.content
    except Exception:
        return getattr(resp.choices[0], "text", str(resp))

async def stream_gpt_messages(messages):
    full = ""
    try:
        try:
            stream_obj = await client.chat.completions.stream(
                model=config.OPENAI_MODEL,
                messages=messages,
                temperature=0.2,
                max_tokens=800
            )
        except TypeError:
            stream_obj = client.chat.completions.stream(
                model=config.OPENAI_MODEL,
                messages=messages,
                temperature=0.2,
                max_tokens=800
            )
        if not hasattr(stream_obj, "__aiter__"):
            log("streaming not available, using sync fallback")
            final_text = ask_gpt(messages[-1]["content"] if messages else "")
            slices = chunk_text_for_tts(final_text)
            for s in slices:
                full += s + " "
                yield {"type": "delta", "content": s + " "}
                await asyncio.sleep(0.05)
            yield {"type": "done", "content": final_text}
            return
        async for part in stream_obj:
            delta = None
            try:
                if hasattr(part, "choices"):
                    ch = part.choices[0]
                    if hasattr(ch, "delta"):
                        d = ch.delta
                        if hasattr(d, "content"):
                            delta = d.content
                        elif isinstance(d, dict):
                            delta = d.get("content")
                    if delta is None and hasattr(ch, "text"):
                        delta = ch.text
                elif isinstance(part, dict):
                    delta = part.get("choices", [{}])[0].get("delta", {}).get("content")
                    if delta is None:
                        delta = part.get("choices", [{}])[0].get("text")
            except Exception:
                delta = None
            if delta:
                full += delta
                yield {"type": "delta", "content": delta}
        yield {"type": "done", "content": full}
    except Exception as e:
        tb = traceback.format_exc()
        log(f"stream_gpt_messages exception: {e}\n{tb}")
        try:
            final_text = ask_gpt(messages[-1]["content"] if messages else "")
            slices = chunk_text_for_tts(final_text)
            for s in slices:
                full += s + " "
                yield {"type": "delta", "content": s + " "}
                await asyncio.sleep(0.05)
            yield {"type": "done", "content": final_text}
        except Exception as e2:
            yield {"type": "error", "content": f"{e} | fallback error: {e2}"}

async def generate_and_stream(session_id, user_text, ws_send):
    try:
        history = get_history(session_id)
        history.append({"role": "user", "content": user_text})
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history

        partial_buffer = ""
        tts_sent_up_to = 0
        loop = asyncio.get_event_loop()

        async for ev in stream_gpt_messages(messages):
            if ev.get("type") == "delta":
                delta = ev.get("content", "")
                partial_buffer += delta
                try:
                    await ws_send({"type": "partial_text", "delta": delta, "full": partial_buffer})
                except Exception as e:
                    log(f"ws_send error partial_text: {e}")
                remaining = partial_buffer[tts_sent_up_to:].strip()
                if len(remaining) >= 40:
                    chunks = chunk_text_for_tts(remaining, max_chars=350, min_chars=40)
                    if chunks:
                        first = chunks[0]
                        tts_sent_up_to += len(first)
                        try:
                            audio_bytes = await loop.run_in_executor(None, elevenlabs_tts_get_audio_bytes, first)
                            b64 = base64.b64encode(audio_bytes).decode()
                            try:
                                await ws_send({"type": "audio_chunk", "text_chunk": first, "audio_b64": b64})
                            except Exception as e:
                                log(f"ws_send error audio_chunk: {e}")
                        except Exception as e:
                            log(f"TTS error for chunk: {e}")
                            try:
                                await ws_send({"type": "error", "message": f"TTS failed: {e}"})
                            except Exception:
                                pass
            elif ev.get("type") == "done":
                final = ev.get("content", "")
                history.append({"role": "assistant", "content": final})
                try:
                    await ws_send({"type": "done", "full": final})
                except Exception as e:
                    log(f"ws_send error done: {e}")
                return
            elif ev.get("type") == "error":
                try:
                    await ws_send({"type": "error", "message": ev.get("content")})
                except Exception:
                    pass
                return

        if partial_buffer:
            history.append({"role": "assistant", "content": partial_buffer})
            try:
                await ws_send({"type": "done", "full": partial_buffer})
            except Exception as e:
                log(f"ws_send error final: {e}")
    except Exception as e:
        tb = traceback.format_exc()
        log(f"generate_and_stream exception: {e}\n{tb}")
        try:
            await ws_send({"type": "error", "message": f"Internal error: {e}"})
        except Exception:
            pass
