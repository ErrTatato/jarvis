# core/jarvis_ai.py
import os
import asyncio
from typing import Optional, AsyncGenerator, Tuple

# Intent parser locale (device/meteo)
from core.intent_router import parse_intent

# Client REST per il gateway FastAPI (device + weather)
from core.actions_client import (
    # Device
    device_flashlight, device_battery, device_wifi, device_bluetooth, device_airplane,
    device_volume, device_screenshot, device_screenrecord, device_notifications,
    device_sms, device_whatsapp, device_call, device_call_end, device_camera_shot,
    # Weather
    wx_current, wx_hourly, wx_daily, wx_aqi, wx_alerts
)

# LLM (solo fallback)
try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None


class JarvisAI:
    def __init__(self):
        self.openai_api_key = os.environ.get("OPENAI_API_KEY", "")
        self.openai_model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        self.client = AsyncOpenAI(api_key=self.openai_api_key) if (self.openai_api_key and AsyncOpenAI) else None

        self.system_prompt = (
            "Sei JARVIS, assistente AI di Tony Stark.\n"
            "Parla italiano, risposte brevi e professionali (1-2 frasi), chiamandomi 'signore'."
        )

    async def handle_text(self, text: str) -> str:
        """
        Entry point: prima prova intent locale (device/meteo), poi fallback al modello.
        Ritorna testo pronto per TTS.
        """
        local = await self._handle_intent_or_none(text)
        if local:
            return local

        if self.client:
            return await self._llm_reply(text)

        return "Al momento non posso rispondere con il modello, signore."

    async def _handle_intent_or_none(self, text: str) -> Optional[str]:
        intent = parse_intent((text or "").strip())
        if not intent:
            return None

        name = intent["name"]
        args = intent.get("args", {})

        try:
            # ===== DEVICE =====
            if name == "flashlight_on":
                res = await device_flashlight(True)
                return "Torcia accesa." if res.get("status") == "success" else "Non ci sono riuscito."
            if name == "flashlight_off":
                res = await device_flashlight(False)
                return "Torcia spenta." if res.get("status") == "success" else "Non ci sono riuscito."

            if name == "battery_status":
                res = await device_battery()
                if res.get("status") == "success":
                    lvl = res["battery"].get("level")
                    if lvl is not None:
                        return f"La batteria è al {lvl} per cento."
                return "Non riesco a leggere la batteria."

            if name == "wifi_on":
                res = await device_wifi(True)
                return "WiFi attivato." if res.get("status") == "success" else "Non ci sono riuscito."
            if name == "wifi_off":
                res = await device_wifi(False)
                return "WiFi disattivato." if res.get("status") == "success" else "Non ci sono riuscito."

            if name == "bt_on":
                res = await device_bluetooth(True)
                return "Bluetooth attivato." if res.get("status") == "success" else "Non ci sono riuscito."
            if name == "bt_off":
                res = await device_bluetooth(False)
                return "Bluetooth disattivato." if res.get("status") == "success" else "Non ci sono riuscito."

            if name == "airplane_on":
                res = await device_airplane(True)
                return "Modalità aereo attivata." if res.get("status") == "success" else "Non ci sono riuscito."
            if name == "airplane_off":
                res = await device_airplane(False)
                return "Modalità aereo disattivata." if res.get("status") == "success" else "Non ci sono riuscito."

            if name == "volume_set":
                lvl = int(args.get("level", 8))
                res = await device_volume(lvl)
                return f"Volume impostato a {lvl}." if res.get("status") == "success" else "Non riesco a impostare il volume."

            if name == "screenshot":
                res = await device_screenshot()
                return "Screenshot eseguito." if res.get("status") == "success" else "Non ci sono riuscito."

            if name == "screenrecord":
                dur = int(args.get("duration", 30))
                res = await device_screenrecord(dur)
                return "Registrazione schermo avviata." if res.get("status") == "success" else "Non ci sono riuscito."

            if name == "notifications":
                res = await device_notifications()
                if res.get("status") == "success":
                    items = res.get("notifications", [])
                    if not items:
                        return "Non ci sono nuove notifiche."
                    preview = "; ".join(items[:3])
                    return f"Ecco le ultime notifiche: {preview}"
                return "Non riesco a leggere le notifiche."

            if name == "sms_send":
                phone = args.get("phone", "")
                message = args.get("message", "")
                res = await device_sms(phone, message)
                return "SMS pronto all'invio." if res.get("status") == "success" else "Non ho potuto preparare l'SMS."

            if name == "wa_send":
                phone = args.get("phone", "")
                message = args.get("message", "")
                res = await device_whatsapp(phone, message)
                return "WhatsApp aperto con il messaggio." if res.get("status") == "success" else "Non sono riuscito ad aprire WhatsApp."

            if name == "call_start":
                phone = args.get("phone", "")
                res = await device_call(phone)
                return f"Sto chiamando {phone}." if res.get("status") == "success" else "Non riesco ad avviare la chiamata."

            if name == "call_end":
                res = await device_call_end()
                return "Chiamata terminata." if res.get("status") == "success" else "Non riesco a terminare la chiamata."

            if name == "camera_shot":
                res = await device_camera_shot()
                return "Foto scattata." if res.get("status") == "success" else "Non sono riuscito a scattare la foto."

            # ===== WEATHER =====
            if name == "weather_now":
                city = args.get("city")
                data = await wx_current(city=city)
                if data.get("status") == "success":
                    main = data["data"].get("main", {})
                    temp = main.get("temp")
                    if temp is not None:
                        target = city or "qui"
                        return f"A {target} ci sono circa {int(round(temp))} gradi."
                return "Non riesco a recuperare il meteo."

            if name == "weather_hourly":
                city = args.get("city")
                data = await wx_hourly(city=city, hours=12)
                return "Ho recuperato le prossime ore di meteo." if data.get("status") == "success" else "Non riesco a recuperare il meteo orario."

            if name == "weather_daily":
                city = args.get("city")
                data = await wx_daily(city=city, days=7)
                return "Ho recuperato la previsione dei prossimi giorni." if data.get("status") == "success" else "Non riesco a recuperare il meteo giornaliero."

        except Exception as e:
            return f"C'è stato un errore nell'esecuzione del comando: {e}"

        return None

    async def _llm_reply(self, user_text: str) -> str:
        """
        Fallback al modello (non streaming) se nessun intent locale.
        """
        try:
            if not self.client:
                return "Il modello non è configurato, signore."
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_text}
            ]
            resp = await self.client.chat.completions.create(
                model=self.openai_model,
                messages=messages,
                temperature=0.6,
                max_tokens=120,
            )
            content = resp.choices[0].message.content.strip()
            return content or "Non ho una risposta migliore, signore."
        except Exception as e:
            return f"Si è verificato un problema nel modello: {e}"


# Singleton per compatibilità
_jarvis_instance: Optional[JarvisAI] = None

def get_jarvis() -> JarvisAI:
    global _jarvis_instance
    if _jarvis_instance is None:
        _jarvis_instance = JarvisAI()
    return _jarvis_instance


async def handle_transcription(text: str) -> str:
    """
    Comodo per pipeline non-streaming: dato testo, ritorna risposta completa.
    """
    jarvis = get_jarvis()
    return await jarvis.handle_text(text)


# ===== Alias richiesto dal tuo server: llm_stream =====
# Manteniamo la firma di compatibilità: AsyncGenerator[Tuple[str, str], None]
# Yield di ("delta", testo_parziale) e infine ("done", "")
async def llm_stream(user_message: str) -> AsyncGenerator[Tuple[str, str], None]:
    """
    Streaming compatibile col tuo server_webrtc:
    - Se esiste un intent locale, streamma la risposta locale in un'unica emissione.
    - Altrimenti streamma la risposta del modello OpenAI se configurato.
    """
    jarvis = get_jarvis()

    # 1) Intent locale
    local = await jarvis._handle_intent_or_none(user_message or "")
    if local:
        yield ("delta", local)
        yield ("done", "")
        return

    # 2) Fallback modello in streaming (se disponibile)
    if jarvis.client:
        messages = [
            {"role": "system", "content": jarvis.system_prompt},
            {"role": "user", "content": user_message or ""}
        ]
        try:
            stream = await jarvis.client.chat.completions.create(
                model=jarvis.openai_model,
                messages=messages,
                temperature=0.6,
                max_tokens=200,
                stream=True
            )
            async for chunk in stream:
                delta = getattr(chunk.choices[0].delta, "content", None)
                if delta:
                    yield ("delta", delta)
            yield ("done", "")
            return
        except Exception as e:
            yield ("delta", f"Si è verificato un problema nel modello: {e}")
            yield ("done", "")
            return

    # 3) Ultimo fallback
    yield ("delta", "Al momento non posso rispondere con il modello, signore.")
    yield ("done", "")
