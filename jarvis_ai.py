import base64
import os
import tempfile
import requests
import whisper
import config
from openai import OpenAI

# OpenAI client (newer SDK)
client = OpenAI(api_key=config.OPENAI_API_KEY)

# Whisper model
model = whisper.load_model("small")
chat_history = []

def save_audio_chunk(audio_base64):
    audio_bytes = base64.b64decode(audio_base64)
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".webm")
    tmp_file.write(audio_bytes)
    tmp_file.close()
    return tmp_file.name

def transcribe_audio_chunk(file_path):
    # Use fp16=False for CPU; returns trimmed string
    result = model.transcribe(file_path, language="it", fp16=False)
    try:
        os.remove(file_path)
    except Exception:
        pass
    return result.get("text", "").strip()

def ask_gpt(prompt):
    global chat_history
    # maintain simple chat history
    chat_history.append({"role": "user", "content": prompt})
    messages = [
        {"role": "system", "content": "Sei Jarvis, l'assistente AI personale di Matteo. Elegante, preciso, ironico. Rispondi in modo conciso e professionale."}
    ] + chat_history

    # Use Responses-like chat completions via new client
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.25,
        max_tokens=450
    )

    # Extract assistant content
    content = ""
    try:
        content = resp.choices[0].message["content"]
    except Exception:
        # fallback for slightly different shape
        try:
            content = resp.choices[0].message.content
        except Exception:
            content = str(resp)

    content = content.strip()
    chat_history.append({"role": "assistant", "content": content})
    return content

def speak(text, return_base64=False):
    if not isinstance(text, str) or not text.strip():
        raise ValueError("speak() called with empty text")

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{config.ELEVENLABS_VOICE_ID}"
    headers = {"xi-api-key": config.ELEVENLABS_API_KEY, "Content-Type": "application/json"}
    data = {"text": text, "voice_settings": {"stability": 0.7, "similarity_boost": 0.8}}

    r = requests.post(url, headers=headers, json=data, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"ElevenLabs TTS failed: {r.status_code} {r.text}")

    if return_base64:
        return base64.b64encode(r.content).decode()

    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tmp_file.write(r.content)
    tmp_file.close()
    return tmp_file.name
