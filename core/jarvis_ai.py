# core/jarvis_ai.py
import os
from typing import Optional, AsyncGenerator, Tuple
import urllib3
import logging

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

from core.actions_client import (
    device_flashlight, device_battery, device_wifi, device_bluetooth, device_airplane,
    device_volume, device_screenshot, device_screenrecord, device_notifications,
    device_sms, device_whatsapp, device_call, device_call_end, device_camera_shot,
    wx_current, wx_hourly, wx_daily, wx_aqi, wx_alerts
)

from core.intent_router import parse_intent

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None

PRIMARY_DEVICE_ID = os.environ.get("JARVIS_PRIMARY_DEVICE_ID", "phone-001")

class JarvisAI:
    def __init__(self):
        self.openai_api_key = os.environ.get("OPENAI_API_KEY", "")
        self.openai_model = os.environ.get("OPENAI_MODEL", "gpt-4o")
        self.client = AsyncOpenAI(api_key=self.openai_api_key) if (self.openai_api_key and AsyncOpenAI) else None

        self.system_prompt = (
            "Sei JARVIS, assistente AI di Tony Stark. Capisci l'italiano e i suoi dialetti e trasformi le richieste in azioni.\n"
            "Se è appropriato, invoca funzioni per controllare smartphone e meteo; risposte brevi (1–2 frasi), chiamandomi 'signore'."
        )

    def tools(self):
        return [
            {"type":"function","function":{"name":"battery_status","description":"Leggi stato batteria del telefono"}},
            {"type":"function","function":{"name":"wifi_toggle","description":"Attiva o disattiva il WiFi","parameters":{"type":"object","properties":{"state":{"type":"boolean"}},"required":["state"]}}},
            {"type":"function","function":{"name":"bt_toggle","description":"Attiva o disattiva il Bluetooth","parameters":{"type":"object","properties":{"state":{"type":"boolean"}},"required":["state"]}}},
            {"type":"function","function":{"name":"airplane_toggle","description":"Attiva o disattiva la modalità aereo","parameters":{"type":"object","properties":{"state":{"type":"boolean"}},"required":["state"]}}},
            {"type":"function","function":{"name":"volume_set","description":"Imposta il volume multimediale (0–15)","parameters":{"type":"object","properties":{"level":{"type":"integer","minimum":0,"maximum":15}},"required":["level"]}}},
            {"type":"function","function":{"name":"flashlight","description":"Accendi/spegni la torcia","parameters":{"type":"object","properties":{"state":{"type":"boolean"}},"required":["state"]}}},
            {"type":"function","function":{"name":"screenshot","description":"Esegui uno screenshot"}},
            {"type":"function","function":{"name":"screenrecord","description":"Registra lo schermo (secondi)","parameters":{"type":"object","properties":{"duration_sec":{"type":"integer","minimum":1,"maximum":180}},"required":["duration_sec"]}}},
            {"type":"function","function":{"name":"notifications_read","description":"Leggi le ultime notifiche"}},
            {"type":"function","function":{"name":"sms_send","description":"Invia un SMS","parameters":{"type":"object","properties":{"phone":{"type":"string"},"message":{"type":"string"}},"required":["phone","message"]}}},
            {"type":"function","function":{"name":"whatsapp_send","description":"Invia un messaggio WhatsApp","parameters":{"type":"object","properties":{"phone":{"type":"string"},"message":{"type":"string"}},"required":["phone","message"]}}},
            {"type":"function","function":{"name":"call_start","description":"Avvia una chiamata","parameters":{"type":"object","properties":{"phone":{"type":"string"}},"required":["phone"]}}},
            {"type":"function","function":{"name":"call_end","description":"Termina la chiamata in corso"}},
            {"type":"function","function":{"name":"camera_shot","description":"Scatta una foto con la fotocamera"}},
            {"type":"function","function":{"name":"weather_now","description":"Meteo attuale","parameters":{"type":"object","properties":{"city":{"type":"string"}}}}},
            {"type":"function","function":{"name":"weather_hourly","description":"Meteo orario","parameters":{"type":"object","properties":{"city":{"type":"string"},"hours":{"type":"integer","minimum":1,"maximum":48}}}}},
            {"type":"function","function":{"name":"weather_daily","description":"Meteo giornaliero","parameters":{"type":"object","properties":{"city":{"type":"string"},"days":{"type":"integer","minimum":1,"maximum":7}}}}},
        ]

    async def handle_text(self, text: str) -> str:
        logger.info(f"[HANDLE_TEXT] Input: {text}")
        fc = await self._try_function_calling(text)
        if fc:
            logger.info(f"[HANDLE_TEXT] Function calling result: {fc}")
            return fc
        local = await self._handle_intent_or_none(text)
        if local:
            logger.info(f"[HANDLE_TEXT] Intent parser result: {local}")
            return local
        result = await self._llm_reply(text)
        logger.info(f"[HANDLE_TEXT] LLM result: {result}")
        return result

    async def _try_function_calling(self, text: str) -> Optional[str]:
        if not self.client:
            logger.warning("[FC] No OpenAI client available")
            return None
        messages = [{"role":"system","content":self.system_prompt},{"role":"user","content":text}]
        try:
            resp = await self.client.chat.completions.create(
                model=self.openai_model,
                messages=messages,
                tools=self.tools(),
                tool_choice="auto",
                temperature=0.4,
                max_completion_tokens=120
            )
            msg = resp.choices[0].message
            tool_calls = getattr(msg, "tool_calls", None)
            if not tool_calls:
                logger.info("[FC] No tool calls returned")
                return None
            tc = tool_calls[0]
            name = tc.function.name
            import json
            args = json.loads(tc.function.arguments or "{}")
            logger.info(f"[FC] Tool call: {name} with args {args}")
            return await self._dispatch(name, args)
        except Exception as e:
            logger.error(f"[FC] Error: {e}")
            return None

    async def _generate_ironic_response(self, prompt: str) -> str:
        try:
            resp = await self.client.chat.completions.create(
                model=self.openai_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.85,
                max_completion_tokens=60
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"[IRONY] Error: {e}")
            return "Sembra che la mia ironia abbia superato anche i miei stessi limiti computazionali."

    async def _dispatch(self, name: str, args: dict) -> str:
        d = PRIMARY_DEVICE_ID
        logger.info(f"[DISPATCH] {name} for device {d}")
        try:
            if name == "battery_status":
                r = await device_battery()
                lvl = (r.get("data") or {}).get("level") or (r.get("battery") or {}).get("level")
                return f"La batteria è al {lvl} per cento." if lvl is not None else "Non riesco a leggere la batteria."
            
            if name == "wifi_toggle":
                r = await device_wifi(d, bool(args["state"]))
                return "WiFi attivato." if r.get("status") == "success" else "Non ci sono riuscito."
            
            if name == "bt_toggle":
                r = await device_bluetooth(d, bool(args["state"]))
                return "Bluetooth attivato." if r.get("status") == "success" else "Non ci sono riuscito."
            
            if name == "airplane_toggle":
                r = await device_airplane(d, bool(args["state"]))
                return "Modalità aereo attivata." if r.get("status") == "success" else "Operazione bloccata dalla ROM."
            
            if name == "volume_set":
                lvl = int(args.get("level", 8))
                logger.info(f"[DISPATCH] Setting volume to {lvl}")
                r = await device_volume(d, lvl)
                logger.info(f"[DISPATCH] Volume response: {r}")
                return f"Volume impostato a {lvl}." if r.get("status") == "success" else f"Non riesco a impostare il volume: {r.get('message', 'sconosciuto')}"
            
            if name == "flashlight":
                r = await device_flashlight(d, bool(args["state"]))
                return "Torcia accesa." if r.get("status") == "success" and args["state"] else ("Torcia spenta." if r.get("status") == "success" else "Operazione non consentita dalla ROM.")
            
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
            
            if name == "weather_now":
                city = args.get("city")
                logger.info(f"[DISPATCH] Getting weather for {city}")
                data = await wx_current(city=city)
                logger.info(f"[DISPATCH] Weather response: {data}")
                if data.get("status") == "success":
                    ddata = (data.get("data") or {})
                    main = ddata.get("main", {}) or {}
                    temp = main.get("temp")
                    if temp is None:
                        temp = ((ddata.get("raw") or {}).get("current") or {}).get("temp_c")
                    description = (((ddata.get("raw") or {}).get("current") or {}).get("condition") or {}).get("text")
                    if not description:
                        description = (ddata.get("weather") or [{}])[0].get("description", "sconosciuto")
                    if temp is not None:
                        prompt = (
                            f"Rispondi come JARVIS (l'IA di Iron Man) in modo ironico ed elegante. "
                            f"Il meteo a {city} è: {int(round(float(temp)))} gradi, {description}. "
                            f"Genera una frase ironica e sofisticata (max 20 parole) con tono da maggiordomo intelligente."
                        )
                        return await self._generate_ironic_response(prompt)
                prompt_error = f"Il sistema meteorologico per {city} è non disponibile. Rispondi in modo ironico come JARVIS in max 15 parole."
                return await self._generate_ironic_response(prompt_error)
            
            if name == "weather_hourly":
                city = args.get("city")
                data = await wx_hourly(city=city, hours=int(args.get("hours", 12)))
                if data.get("status") == "success":
                    hourly = (data.get("data") or {}).get("hourly", [])
                    if hourly:
                        temps = [int(h.get("temp_c", h.get("temp", 0))) for h in hourly[:6]]
                        cond = (hourly[0].get("condition") or {}).get("text") or hourly[0].get("description", "variabile")
                        prompt = (
                            f"Come JARVIS, commenta ironicamente il meteo delle prossime ore a {city}: {cond}, "
                            f"temperature da {min(temps)}° a {max(temps)}°C. Massimo 18 parole, tono elegante e leggermente sarcastico."
                        )
                        return await self._generate_ironic_response(prompt)
                return f"Non riesco a recuperare il meteo per {city}: {data.get('message', 'errore sconosciuto')}"
            
            if name == "weather_daily":
                city = args.get("city")
                data = await wx_daily(city=city, days=int(args.get("days", 7)))
                if data.get("status") == "success":
                    root = (data.get("data") or {})
                    daily = (root.get("forecast") or {}).get("forecastday", []) or ((root.get("raw") or {}).get("forecast") or {}).get("forecastday", [])
                    if daily:
                        day = daily[0].get("day", {})
                        max_t = int(day.get("maxtemp_c", day.get("max_temp", 20)))
                        min_t = int(day.get("mintemp_c", day.get("min_temp", 10)))
                        cond = (day.get("condition") or {}).get("text") or day.get("description", "incerto")
                        prompt = (
                            f"Come JARVIS, commenta con elegante ironia le previsioni di oggi a {city}: {cond}, "
                            f"da {min_t}° a {max_t}°C. Una frase sola, massimo 18 parole, tono sofisticato e leggermente sarcastico."
                        )
                        return await self._generate_ironic_response(prompt)
                return f"Le previsioni meteorologiche per {city} rimangono imperscrutabili, anche per la mia intelligenza."
        
        except Exception as e:
            logger.error(f"[DISPATCH] Exception: {e}")
            return f"C'è stato un errore nell'esecuzione del comando: {e}"
        
        return "Richiesta non riconosciuta, signore."

    async def _handle_intent_or_none(self, text: str) -> Optional[str]:
        intent = parse_intent((text or "").strip())
        if not intent:
            logger.info("[INTENT] No intent matched")
            return None
        name = intent["name"]
        args = intent.get("args", {})
        logger.info(f"[INTENT] Matched: {name}")
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
                max_completion_tokens=140
            )
            content = resp.choices[0].message.content
            return (content or "").strip() or "Non ho una risposta migliore, signore."
        except Exception as e:
            logger.error(f"[LLM] Error: {e}")
            return f"Si è verificato un problema nel modello: {e}"

_jarvis_instance: Optional[JarvisAI] = None

def get_jarvis() -> JarvisAI:
    global _jarvis_instance
    if _jarvis_instance is None:
        _jarvis_instance = JarvisAI()
    return _jarvis_instance

async def handle_transcription(text: str) -> str:
    jarvis = get_jarvis()
    return await jarvis.handle_text(text)

async def llm_stream(user_message: str) -> AsyncGenerator[Tuple[str, str], None]:
    jarvis = get_jarvis()
    fc = await jarvis._try_function_calling(user_message or "")
    if fc:
        yield ("delta", fc); yield ("done",""); return
    local = await jarvis._handle_intent_or_none(user_message or "")
    if local:
        yield ("delta", local); yield ("done",""); return
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
                max_completion_tokens=200,
                stream=True
            )
            async for chunk in stream:
                delta = getattr(chunk.choices[0].delta, "content", None)
                if delta: yield ("delta", delta)
            yield ("done",""); return
        except Exception as e:
            logger.error(f"[STREAM] Error: {e}")
            yield ("delta", f"Si è verificato un problema nel modello: {e}")
            yield ("done",""); return
    yield ("delta", "Al momento non posso rispondere con il modello, signore."); yield ("done","")
