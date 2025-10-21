import whisper
import requests
from flask import Flask, request, send_file
from pydub import AudioSegment
import config
import os

app = Flask(__name__)

# Carica modello Whisper italiano
model = whisper.load_model("small")  # tiny/medium/large se vuoi

# Funzione GPT-4-mini
def ask_gpt(prompt):
    import openai
    openai.api_key = config.OPENAI_API_KEY
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# Funzione ElevenLabs TTS
def speak_elevenlabs(text, output_file="audio.mp3"):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{config.ELEVENLABS_VOICE_ID}"
    headers = {
        "xi-api-key": config.ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "text": text,
        "voice_settings": {"stability":0.7, "similarity_boost":0.8}
    }
    r = requests.post(url, headers=headers, json=data)
    with open(output_file, "wb") as f:
        f.write(r.content)
    return output_file

# Endpoint per ricevere audio dal telefono
@app.route("/ask", methods=["POST"])
def ask():
    audio_file = request.files["audio"]
    audio_path = f"audio/{audio_file.filename}"
    audio_file.save(audio_path)

    # Trascrizione con Whisper
    result = model.transcribe(audio_path, language="it")
    text_input = result["text"]

    # Invio a GPT
    response_text = ask_gpt(text_input)

    # TTS ElevenLabs
    audio_response = speak_elevenlabs(response_text, output_file=f"audio/resp_{audio_file.filename}.mp3")
    
    return send_file(audio_response, mimetype="audio/mpeg")

if __name__ == "__main__":
    app.run(host=config.HOST, port=config.PORT)
