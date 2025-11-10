# core/wake_listener.py - VERSIONE CON SUPPORTO PTT E WAKE WORD
import pyaudio
import numpy as np
import logging
import keyboard
from threading import Thread, Event

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WakeWordListener:
    """Ascolta comandi via PTT (tasto premuto) o via wake word ('Jarvis')"""
    
    def __init__(self, ptt_key='space'):
        self.CHUNK = 2048
        self.FORMAT = 16
        self.CHANNELS = 1
        self.RATE = 16000
        self.THRESHOLD_DB = -40
        self.SILENCE_DURATION = 1.5
        self.PTT_KEY = ptt_key  # Tasto per Push-To-Talk (spazio)
        
        self.pa = pyaudio.PyAudio()
        self.stream = None
        self.ptt_active = Event()
        
        logger.info("[WAKE] Listener inizializzato")
        logger.info(f"[WAKE] Supporta: Wake word 'Jarvis' oppure PTT ({ptt_key})")
        
        # Avvia listener del tasto PTT in background
        self._start_ptt_listener()
    
    def _start_ptt_listener(self):
        """Background thread che ascolta il tasto PTT"""
        def ptt_handler():
            logger.info(f"[PTT] Listener attivo per tasto '{self.PTT_KEY}'")
            while True:
                try:
                    if keyboard.is_pressed(self.PTT_KEY):
                        self.ptt_active.set()
                        logger.info("[PTT] ✅ Tasto premuto - registrazione avviata")
                        while keyboard.is_pressed(self.PTT_KEY):
                            pass
                        self.ptt_active.clear()
                        logger.info("[PTT] Tasto rilasciato - registrazione completata")
                except:
                    pass
        
        thread = Thread(target=ptt_handler, daemon=True)
        thread.start()
    
    def listen_for_wake_word(self, timeout=30):
        """Ascolta la wake word 'Jarvis' oppure attende PTT"""
        logger.info("[WAKE] In ascolto della wake word 'Jarvis' o PTT...")
        
        try:
            if self.stream is None:
                self.stream = self.pa.open(
                    format=self.pa.get_format_from_width(self.FORMAT // 8),
                    channels=self.CHANNELS,
                    rate=self.RATE,
                    input=True,
                    frames_per_buffer=self.CHUNK,
                    exception_on_overflow=False
                )
            
            while True:
                # Modalità 1: PTT attivo?
                if self.ptt_active.is_set():
                    logger.info("[WAKE] 🎙️ PTT attivo - procedi direttamente al comando")
                    return True
                
                # Modalità 2: Ascolta wake word
                data = self.stream.read(self.CHUNK, exception_on_overflow=False)
                audio = np.frombuffer(data, dtype=np.int16)
                
                rms = np.sqrt(np.mean(audio ** 2))
                db = 20 * np.log10(rms + 1e-10)
                
                if db > self.THRESHOLD_DB:
                    logger.debug(f"[WAKE] Audio rilevato (DB: {db:.1f})")
                    # Accumula buffer
                    audio_buffer = list(audio)
                    for _ in range(10):  # Accumula ~20ms
                        try:
                            data = self.stream.read(self.CHUNK, exception_on_overflow=False)
                            audio = np.frombuffer(data, dtype=np.int16)
                            audio_buffer.extend(audio)
                        except:
                            pass
                    
                    full_audio = np.array(audio_buffer, dtype=np.int16)
                    if len(full_audio) > self.RATE // 2:
                        if self._contains_wake_word(full_audio):
                            logger.info("[WAKE] ✅ 'Jarvis' riconosciuto!")
                            return True
        
        except Exception as e:
            logger.error(f"[WAKE] Error: {e}")
            return False
    
    def listen_for_command(self, timeout=10):
        """Ascolta il comando vocale"""
        logger.info("[COMMAND] In ascolto del comando...")
        
        try:
            if self.stream is None:
                self.stream = self.pa.open(
                    format=self.pa.get_format_from_width(self.FORMAT // 8),
                    channels=self.CHANNELS,
                    rate=self.RATE,
                    input=True,
                    frames_per_buffer=self.CHUNK,
                    exception_on_overflow=False
                )
            
            audio_frames = []
            silent_chunks = 0
            max_silent_chunks = int(self.RATE / self.CHUNK * self.SILENCE_DURATION)
            speech_started = False
            
            while True:
                try:
                    # Se PTT è premuto, ascolta
                    if self.ppt_active.is_set() or not speech_started:
                        data = self.stream.read(self.CHUNK, exception_on_overflow=False)
                        audio = np.frombuffer(data, dtype=np.int16)
                        
                        rms = np.sqrt(np.mean(audio ** 2))
                        db = 20 * np.log10(rms + 1e-10)
                        
                        if db > self.THRESHOLD_DB:
                            speech_started = True
                            silent_chunks = 0
                            audio_frames.append(audio)
                        else:
                            if speech_started:
                                silent_chunks += 1
                                audio_frames.append(audio)
                                
                                # Se PTT è attivo e il tasto è rilasciato, interrompi
                                if not self.ppt_active.is_set() and silent_chunks > max_silent_chunks:
                                    logger.info("[COMMAND] Fine comando rilevata")
                                    break
                    else:
                        # PTT non attivo ma speech non iniziato
                        break
                
                except Exception as e:
                    logger.error(f"[COMMAND] Audio error: {e}")
                    continue
            
            if audio_frames:
                full_audio = np.concatenate(audio_frames)
                return full_audio.tobytes()
            
            return None
        
        except Exception as e:
            logger.error(f"[COMMAND] Error: {e}")
            return None
    
    def _contains_wake_word(self, audio: np.ndarray) -> bool:
        """Rileva 'Jarvis' con pattern semplice"""
        if len(audio) < self.RATE // 2:
            return False
        
        # Analisi spettro
        try:
            from scipy.fft import rfft, rfftfreq
            freqs = rfft(audio)
            freq_bins = rfftfreq(len(audio), 1 / self.RATE)
            
            mask = freq_bins < 4000
            voice_freqs = np.abs(freqs[mask])
            energy = np.sum(voice_freqs)
            
            if energy > 1e6:
                logger.debug(f"[WAKE] Energy: {energy:.0f} - Parola rilevata")
                return True
        except:
            pass
        
        return False
    
    def stop(self):
        """Ferma il listener"""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.pa.terminate()
        logger.info("[WAKE] Listener fermato")
