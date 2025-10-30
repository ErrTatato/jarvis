# core/jarvis_ai.py
import os
from typing import Optional, AsyncGenerator, Tuple

# Client REST per il gateway FastAPI (device + weather)
from core.actions_client import (
    # Device (richiedono device_id)
    device_flashlight, device_battery, device_wifi, device_bluetooth, device_airplane,
    device_volume, device_screenshot, device_screenrecord, device_notifications,
    device_sms, device_whatsapp, device_call, device_call_end, device_camera_shot,
    # Weather
    wx_current, wx_hourly, wx_daily, wx_aqi, wx_alerts
)

# Intent parser locale per comandi rapidi (fallback se il modello non invoca tool)
from core.intent_router import parse_intent

# LLM (function-calling per capire frasi libere)
try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None


PRIMARY_DEVICE_ID = os.environ.get("JARVIS_PRIMARY_DEVICE_ID", "phone-001")


class JarvisAI:
    def __init__(self):
        self.openai_api_key = os.environ.get("OPENAI_API_KEY", "")
        self.openai_model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        self.client = AsyncOpenAI(api_key=self.openai_api_key) if (self.openai_api_key and AsyncOpenAI) else None

        # Istruzioni concise: capisci la richiesta, scegli l'azione, chiedi argomenti mancanti solo se indispensabili.
        self.system_prompt = (
            "Sei JARVIS, assistente AI di Tony Stark. Capisci l'italiano colloquiale e trasformi le richieste in azioni.\n"
            "Se Ã¨ appropriato, invoca funzioni per controllare smartphone e meteo; risposte brevi (1â€‘2 frasi), chiamandomi 'signore'."
        )

    def tools(self):
        # Strumenti che il modello puÃ² invocare per decidere l'azione corretta in linguaggio naturale.
        return [
            {"type":"function","function":{"name":"battery_status","description":"Leggi stato batteria del telefono"}},
            {"type":"function","function":{"name":"wifi_toggle","description":"Attiva o disattiva il Wiâ€‘Fi","parameters":{"type":"object","properties":{"state":{"type":"boolean"}},"required":["state"]}}},
            {"type":"function","function":{"name":"bt_toggle","description":"Attiva o disattiva il Bluetooth","parameters":{"type":"object","properties":{"state":{"type":"boolean"}},"required":["state"]}}},
            {"type":"function","function":{"name":"airplane_toggle","description":"Attiva o disattiva la modalitÃ  aereo","parameters":{"type":"object","properties":{"state":{"type":"boolean"}},"required":["state"]}}},
            {"type":"function","function":{"name":"volume_set","description":"Imposta il volume multimediale (0â€‘15)","parameters":{"type":"object","properties":{"level":{"type":"integer","minimum":0,"maximum":15}},"required":["level"]}}},
            {"type":"function","function":{"name":"flashlight","description":"Accendi/spegni la torcia","parameters":{"type":"object","properties":{"state":{"type":"boolean"}},"required":["state"]}}},
            {"type":"function","function":{"name":"screenshot","description":"Esegui uno screenshot"}},
            {"type":"function","function":{"name":"screenrecord","description":"Registra lo schermo (secondi)","parameters":{"type":"object","properties":{"duration_sec":{"type":"integer","minimum":1,"maximum":180}},"required":["duration_sec"]}}},
            {"type":"function","function":{"name":"notifications_read","description":"Leggi le ultime notifiche"}},
            {"type":"function","function":{"name":"sms_send","description":"Invia un SMS","parameters":{"type":"object","properties":{"phone":{"type":"string"},"message":{"type":"string"}},"required":["phone","message"]}}},
            {"type":"function","function":{"name":"whatsapp_send","description":"Invia un messaggio WhatsApp","parameters":{"type":"object","properties":{"phone":{"type":"string"},"message":{"type":"string"}},"required":["phone","message"]}}},
            {"type":"function","function":{"name":"call_start","description":"Avvia una chiamata","parameters":{"type":"object","properties":{"phone":{"type":"string"}},"required":["phone"]}}},
            {"type":"function","function":{"name":"call_end","description":"Termina la chiamata in corso"}},
            {"type":"function","function":{"name":"camera_shot","description":"Scatta una foto con la fotocamera"}},
            # Weather
            {"type":"function","function":{"name":"weather_now","description":"Meteo attuale","parameters":{"type":"object","properties":{"city":{"type":"string"}}}}},
            {"type":"function","function":{"name":"weather_hourly","description":"Meteo orario","parameters":{"type":"object","properties":{"city":{"type":"string"},"hours":{"type":"integer","minimum":1,"maximum":48}}}}},
            {"type":"function","function":{"name":"weather_daily","description":"Meteo giornaliero","parameters":{"type":"object","properties":{"city":{"type":"string"},"days":{"type":"integer","minimum":1,"maximum":7}}}}},
        ]

    async def handle_text(self, text: str) -> str:
        """
        Flusso: prova prima con function-calling (NL â†’ azione). Se non vengono invocati tool,
        prova l'intent parser locale; infine, fallback risposta LLM.
        """
        # 1) Function-calling
        fc = await self._try_function_calling(text)
        if fc:
            return fc

        # 2) Intent parser locale (backup)
        local = await self._handle_intent_or_none(text)
        if local:
            return local

        # 3) Fallback generativo
        return await self._llm_reply(text)

    async def _try_function_calling(self, text: str) -> Optional[str]:
        if not self.client:
            return None
        messages = [{"role":"system","content":self.system_prompt},{"role":"user","content":text}]
        resp = await self.client.chat.completions.create(
            model=self.openai_model,
            messages=messages,
            tools=self.tools(),
            tool_choice="auto",
            temperature=0.4,
            max_tokens=120
        )
        msg = resp.choices[0].message
        tool_calls = getattr(msg, "tool_calls", None)
        if not tool_calls:
            return None
        # Esegui la prima tool call rilevante
        tc = tool_calls[0]
        name = tc.function.name
        import json
        args = json.loads(tc.function.arguments or "{}")
        return await self._dispatch(name, args)

    async def _dispatch(self, name: str, args: dict) -> str:
        d = PRIMARY_DEVICE_ID

        # ===== DEVICE via hub remoto =====
        try:
            if name == "battery_status":
                r = await device_battery(d)
                lvl = (r.get("data") or {}).get("level") or (r.get("battery") or {}).get("level")
                return f"La batteria Ã¨ al {lvl} per cento." if lvl is not None else "Non riesco a leggere la batteria."

            if name == "wifi_toggle":
                r = await device_wifi(d, bool(args["state"]))
                return "WiFi attivato." if r.get("status") == "success" else "Non ci sono riuscito."

            if name == "bt_toggle":
                r = await device_bluetooth(d, bool(args["state"]))
                return "Bluetooth attivato." if r.get("status") == "success" else "Non ci sono riuscito."

            if name == "airplane_toggle":
                r = await device_airplane(d, bool(args["state"]))
                return "ModalitÃ  aereo attivata." if r.get("status") == "success" else "Operazione bloccata dalla ROM."

            if name == "volume_set":
                lvl = int(args.get("level", 8))
                r = await device_volume(d, lvl)
                return f"Volume impostato a {lvl}." if r.get("status") == "success" else "Non riesco a impostare il volume."

            if name == "flashlight":
                r = await device_flashlight(d, bool(args["state"]))
                return "Torcia accesa." if r.get("status") == "success" and args["state"] else \
                       ("Torcia spenta." if r.get("status") == "success" else "Operazione non consentita dalla ROM.")

            if name == "screenshot":
                r = await device_screenshot(d)
                return "Screenshot eseguito." if r.get("status") == "success" else "Non ci sono riuscito."

            if name == "screenrecord":
                dur = int(args.get("duration_sec", 30))
                r = await device_screenrecord(d, dur)
                return "Registrazione schermo avviata." if r.get("status") == "success" else "Non ci sono riuscito."

            if name == "notifications_read":
                r = await device_notifications(d)
                items = (r.get("data") or {}).get("items") or r.get("notifications") or []
                return "Non ci sono nuove notifiche." if not items else f"Ecco le ultime notifiche: {'; '.join(items[:3])}"

            if name == "sms_send":
                r = await device_sms(d, args.get("phone",""), args.get("message",""))
                return "SMS inviato o pronto all'invio." if r.get("status") == "success" else "Non sono riuscito a preparare l'SMS."

            if name == "whatsapp_send":
                r = await device_whatsapp(d, args.get("phone",""), args.get("message",""))
                return "WhatsApp aperto con il messaggio." if r.get("status") == "success" else "Non riesco ad aprire WhatsApp."

            if name == "call_start":
                phone = args.get("phone","")
                r = await device_call(d, phone)
                return "Chiamata avviata." if r.get("status") == "success" else "Ho aperto il dialer."

            if name == "call_end":
                r = await device_call_end(d)
                return "Chiamata terminata." if r.get("status") == "success" else "Non riesco a terminare la chiamata."

            if name == "camera_shot":
                r = await device_camera_shot(d)
                return "Foto scattata." if r.get("status") == "success" else "Non sono riuscito a scattare la foto."

            # ===== WEATHER =====
            if name == "weather_now":
                city = args.get("city")
                data = await wx_current(city=city)
                if data.get("status") == "success":
                    main = (data.get("data") or {}).get("main", {})
                    temp = main.get("temp")
                    if temp is not None:
                        return f"A {city or 'qui'} ci sono circa {int(round(temp))} gradi."
                return "Non riesco a recuperare il meteo."

            if name == "weather_hourly":
                city = args.get("city")
                data = await wx_hourly(city=city, hours=int(args.get("hours", 12)))
                return "Ho recuperato il meteo orario." if data.get("status") == "success" else "Non riesco a recuperare il meteo orario."

            if name == "weather_daily":
                city = args.get("city")
                data = await wx_daily(city=city, days=int(args.get("days", 7)))
                return "Ho recuperato la previsione dei prossimi giorni." if data.get("status") == "success" else "Non riesco a recuperare il meteo giornaliero."

        except Exception as e:
            return f"C'Ã¨ stato un errore nell'esecuzione del comando: {e}"

        return "Richiesta non riconosciuta, signore."

    async def _handle_intent_or_none(self, text: str) -> Optional[str]:
        """
        Intent parser locale: utile se il modello non ha invocato tool.
        """
        intent = parse_intent((text or "").strip())
        if not intent:
            return None
        name = intent["name"]
        args = intent.get("args", {})
        # Riusa _dispatch mappando l'intent su tool equivalenti
        mapping = {
            "flashlight_on": ("flashlight", {"state": True}),
            "flashlight_off": ("flashlight", {"state": False}),
            "battery_status": ("battery_status", {}),
            "wifi_on": ("wifi_toggle", {"state": True}),
            "wifi_off": ("wifi_toggle", {"state": False}),
            "bt_on": ("bt_toggle", {"state": True}),
            "bt_off": ("bt_toggle", {"state": False}),
            "airplane_on": ("airplane_toggle", {"state": True}),
            "airplane_off": ("airplane_toggle", {"state": False}),
            "volume_set": ("volume_set", {"level": int(args.get("level", 8))}),
            "screenshot": ("screenshot", {}),
            "screenrecord": ("screenrecord", {"duration_sec": int(args.get("duration", 30))}),
            "notifications": ("notifications_read", {}),
            "sms_send": ("sms_send", {"phone": args.get("phone",""), "message": args.get("message","")}),
            "wa_send": ("whatsapp_send", {"phone": args.get("phone",""), "message": args.get("message","")}),
            "call_start": ("call_start", {"phone": args.get("phone","")}),
            "call_end": ("call_end", {}),
            "camera_shot": ("camera_shot", {}),
            "weather_now": ("weather_now", {"city": args.get("city")}),
            "weather_hourly": ("weather_hourly", {"city": args.get("city"), "hours": 12}),
            "weather_daily": ("weather_daily", {"city": args.get("city"), "days": 7}),
        }
        tool = mapping.get(name)
        if not tool:
            return None
        tname, targs = tool
        return await self._dispatch(tname, targs)

    async def _llm_reply(self, user_text: str) -> str:
        """
        Risposta generativa quando non c'Ã¨ azione da compiere.
        """
        if not self.client:
            return "Al momento non posso rispondere con il modello, signore."
        try:
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_text}
            ]
            resp = await self.client.chat.completions.create(
                model=self.openai_model,
                messages=messages,
                temperature=0.6,
                max_tokens=140,
            )
            content = resp.choices[0].message.content
            return (content or "").strip() or "Non ho una risposta migliore, signore."
        except Exception as e:
            return f"Si Ã¨ verificato un problema nel modello: {e}"


# Singleton per compatibilitÃ 
_jarvis_instance: Optional[JarvisAI] = None

def get_jarvis() -> JarvisAI:
    global _jarvis_instance
    if _jarvis_instance is None:
        _jarvis_instance = JarvisAI()
    return _jarvis_instance

async def handle_transcription(text: str) -> str:
    """
    Entry point nonâ€‘streaming: testo â†’ risposta.
    """
    jarvis = get_jarvis()
    return await jarvis.handle_text(text)

# Streaming compatibile con server_webrtc
async def llm_stream(user_message: str) -> AsyncGenerator[Tuple[str, str], None]:
    jarvis = get_jarvis()
    # Prova function-calling
    fc = await jarvis._try_function_calling(user_message or "")
    if fc:
        yield ("delta", fc); yield ("done",""); return
    # Intent parser
    local = await jarvis._handle_intent_or_none(user_message or "")
    if local:
        yield ("delta", local); yield ("done",""); return
    # Fallback generativo
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
                if delta: yield ("delta", delta)
            yield ("done",""); return
        except Exception as e:
            yield ("delta", f"Si Ã¨ verificato un problema nel modello: {e}")
            yield ("done",""); return
    yield ("delta", "Al momento non posso rispondere con il modello, signore."); yield ("done","")
