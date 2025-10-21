# jarvis_ai.py
import openai
import whisper
import requests
import tempfile
import os
import config

# API key
openai.api_key = config.OPENAI_API_KEY

# Carica modello Whisper
model = whisper.load_model("small")

# GPT
def ask_gpt(prompt: str) -> str:
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# ElevenLabs TTS
def speak(text: str) -> str:
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{config.ELEVENLABS_VOICE_ID}"
    headers = {"xi-api-key": config.ELEVENLABS_API_KEY, "Content-Type": "application/json"}
    data = {"text": text, "voice_settings": {"stability": 0.5, "similarity_boost": 0.85, "rate": 1.25}}
    r = requests.post(url, headers=headers, json=data, timeout=60)
    r.raise_for_status()
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    temp.write(r.content)
    temp.flush()
    temp.close()
    return temp.name

# Trascrizione
def transcribe_audio(file_path: str) -> str:
    result = model.transcribe(file_path, language="it")
    return result["text"]
