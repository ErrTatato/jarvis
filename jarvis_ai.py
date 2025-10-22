import openai
import whisper
import requests
import tempfile
import os
import base64
import config

openai.api_key = config.OPENAI_API_KEY

# Carica modello Whisper
model = whisper.load_model("small")

# Gestione chunk audio temporanei
def save_audio_chunk(audio_base64):
    audio_bytes = base64.b64decode(audio_base64)
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".webm")
    tmp_file.write(audio_bytes)
    tmp_file.close()
    return tmp_file.name

def transcribe_audio_chunk(file_path):
    # Trascrizione con Whisper
    result = model.transcribe(file_path, language="it")
    os.remove(file_path)
    return result["text"]

# GPT
def ask_gpt(prompt):
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# ElevenLabs TTS
def speak(text, return_base64=False):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{config.ELEVENLABS_VOICE_ID}"
    headers = {"xi-api-key": config.ELEVENLABS_API_KEY, "Content-Type": "application/json"}
    data = {"text": text, "voice_settings": {"stability": 0.7, "similarity_boost": 0.8}}
    r = requests.post(url, headers=headers, json=data)
    if return_base64:
        return base64.b64encode(r.content).decode()
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tmp_file.write(r.content)
    tmp_file.close()
    return tmp_file.name
