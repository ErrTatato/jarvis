import logging
from typing import Optional
from openai import OpenAI

try:
    from google.cloud import texttospeech
    GOOGLE_TTS_AVAILABLE = True
except ImportError:
    GOOGLE_TTS_AVAILABLE = False

logger = logging.getLogger("JARVIS.TTS")

class TTSService:
    """Service per Text-to-Speech"""
    
    def __init__(self, openai_client: OpenAI, language: str = "it-IT"):
        self.openai = openai_client
        self.language = language
        
        self.google_client = None
        if GOOGLE_TTS_AVAILABLE:
            try:
                self.google_client = texttospeech.TextToSpeechClient()
                logger.info("✅ Google TTS available")
            except Exception as e:
                logger.warning(f"Google TTS unavailable: {e}")
    
    async def text_to_speech_google(self, text: str) -> Optional[bytes]:
        """Usa Google TTS (italiano puro)"""
        if not self.google_client:
            return None
        
        try:
            synthesis_input = texttospeech.SynthesisInput(text=text)
            voice = texttospeech.VoiceSelectionParams(
                language_code=self.language,
                name="it-IT-Neural2-A"
            )
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3
            )
            
            response = self.google_client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            
            logger.info(f"🎙️ Google TTS: {len(text)} chars")
            return response.audio_content
        
        except Exception as e:
            logger.error(f"Google TTS error: {e}")
            return None
    
    async def text_to_speech(self, text: str, voice: str = "onyx") -> Optional[bytes]:
        """TTS con fallback (Google → OpenAI)"""
        # Prova Google prima
        google_audio = await self.text_to_speech_google(text)
        if google_audio:
            return google_audio
        
        # Fallback OpenAI
        try:
            response = self.openai.audio.speech.create(
                model="tts-1-hd",
                voice=voice,
                input=text,
                speed=1.0
            )
            logger.info(f"🎙️ OpenAI TTS: {len(text)} chars")
            return response.content
        
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return None