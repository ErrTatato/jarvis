import pvporcupine
import pyaudio
import requests
import config
import logging
import time

logging.basicConfig(level=logging.INFO)

def run_wake_listener(server_url=None):
    if server_url is None:
        server_url = f"https://{config.HOST}:{config.PORT}/wake"

    porcupine = pvporcupine.create(keywords=["jarvis"])
    pa = pyaudio.PyAudio()
    stream = pa.open(format=pyaudio.paInt16, channels=1, rate=porcupine.sample_rate,
                     input=True, frames_per_buffer=porcupine.frame_length)

    logging.info("Wake listener attivo, in attesa di 'Jarvis'...")

    try:
        while True:
            pcm = stream.read(porcupine.frame_length, exception_on_overflow=False)
            pcm_unpacked = [int.from_bytes(pcm[i:i+2], 'little', signed=True) for i in range(0, len(pcm), 2)]
            keyword_index = porcupine.process(pcm_unpacked)
            if keyword_index >= 0:
                logging.info("Trigger vocale rilevato")
                try:
                    r = requests.post(server_url, timeout=5, verify=False)
                    logging.info(f"Wake POST status: {r.status_code}")
                except Exception as e:
                    logging.error(f"Errore invio trigger al server: {e}")
                time.sleep(1.2)
    except KeyboardInterrupt:
        logging.info("Wake listener interrotto")
    finally:
        stream.stop_stream()
        stream.close()
        pa.terminate()
        porcupine.delete()

if __name__ == "__main__":
    run_wake_listener()
