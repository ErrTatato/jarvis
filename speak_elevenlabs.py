import requests
import config

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
