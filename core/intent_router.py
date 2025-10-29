import re

def parse_intent(text: str):
    t = text.lower().strip()

    # Torcia
    if re.search(r"\b(accendi|attiva)\b.*\btorcia\b", t):
        return {"name": "flashlight_on", "args": {}}
    if re.search(r"\b(spegni|disattiva)\b.*\btorcia\b", t):
        return {"name": "flashlight_off", "args": {}}

    # Batteria
    if "batteria" in t:
        return {"name": "battery_status", "args": {}}

    # WiFi
    if re.search(r"(attiva|accendi).*(wifi|wi-fi)", t):
        return {"name": "wifi_on", "args": {}}
    if re.search(r"(disattiva|spegni).*(wifi|wi-fi)", t):
        return {"name": "wifi_off", "args": {}}

    # Bluetooth
    if re.search(r"(attiva|accendi).*(bluetooth)", t):
        return {"name": "bt_on", "args": {}}
    if re.search(r"(disattiva|spegni).*(bluetooth)", t):
        return {"name": "bt_off", "args": {}}

    # Aereo
    if re.search(r"(attiva|accendi).*(modalit[aà] aereo)", t):
        return {"name": "airplane_on", "args": {}}
    if re.search(r"(disattiva|spegni).*(modalit[aà] aereo)", t):
        return {"name": "airplane_off", "args": {}}

    # Volume
    m = re.search(r"volume.*(?:a|al)\s*(\d{1,2})", t)
    if m:
        lvl = int(m.group(1))
        return {"name": "volume_set", "args": {"level": lvl}}
    if "alza il volume" in t:
        return {"name": "volume_set", "args": {"level": 12}}
    if "abbassa il volume" in t:
        return {"name": "volume_set", "args": {"level": 4}}

    # Screenshot / screenrecord
    if "screenshot" in t:
        return {"name": "screenshot", "args": {}}
    if "registra schermo" in t or "registrare lo schermo" in t:
        m = re.search(r"(\d+)\s*(secondo|secondi)", t)
        dur = int(m.group(1)) if m else 30
        return {"name": "screenrecord", "args": {"duration": dur}}

    # Notifiche
    if "notifiche" in t:
        return {"name": "notifications", "args": {}}

    # SMS / WhatsApp
    if "invia sms" in t:
        m = re.search(r"invia sms (?:a|al)\s*([0-9+ ]+)\s*(.+)$", t)
        if m:
            return {"name": "sms_send", "args": {"phone": m.group(1).strip(), "message": m.group(2).strip()}}
        return {"name": "sms_send", "args": {"phone": "", "message": ""}}
    if "whatsapp" in t or "whatsApp" in text:
        m = re.search(r"whatsapp (?:a|al)\s*([0-9+ ]+)\s*(.+)$", t)
        if m:
            return {"name": "wa_send", "args": {"phone": m.group(1).strip(), "message": m.group(2).strip()}}
        return {"name": "wa_send", "args": {"phone": "", "message": ""}}

    # Chiamate
    if re.search(r"\bchiama\b", t):
        m = re.search(r"chiama\s*([0-9+ ]+)", t)
        phone = m.group(1).strip() if m else ""
        return {"name": "call_start", "args": {"phone": phone}}
    if "riaggancia" in t or "termina chiamata" in t:
        return {"name": "call_end", "args": {}}

    # Meteo
    if any(k in t for k in ["meteo", "che tempo", "temperatura", "piove", "pioverà"]):
        # città basica: "a Roma", "a Milano"
        m = re.search(r"a\s+([a-zàèéìòù]+)", t)
        city = m.group(1).capitalize() if m else None
        if "domani" in t or "settimana" in t:
            return {"name": "weather_daily", "args": {"city": city}}
        if "ore" in t or "orarie" in t or "oggi pomeriggio" in t:
            return {"name": "weather_hourly", "args": {"city": city}}
        return {"name": "weather_now", "args": {"city": city}}

    return None
