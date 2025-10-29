import os
import time
import subprocess

ADB = os.environ.get("ADB_PATH", "adb")

def _run(cmd: list[str], timeout: int = 10):
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return {"ok": res.returncode == 0, "stdout": res.stdout.strip(), "stderr": res.stderr.strip()}
    except Exception as e:
        return {"ok": False, "stdout": "", "stderr": str(e)}

def _ensure_device():
    out = _run([ADB, "devices"])
    if not out["ok"]:
        return False
    return any(l.endswith("\tdevice") for l in out["stdout"].splitlines())

def get_battery_status():
    if not _ensure_device():
        return {"status": "error", "message": "No Android device detected (ADB)"}
    out = _run([ADB, "shell", "dumpsys", "battery"])
    info = {}
    for line in out["stdout"].splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            info[k.strip()] = v.strip()
    return {"status": "success", "battery": {
        "level": int(info.get("level", "0")),
        "status": info.get("status"),
        "health": info.get("health"),
        "temperature_c": float(info.get("temperature", "0")) / 10.0,
        "plugged": info.get("AC powered") == "true" or info.get("USB powered") == "true",
    }}

def toggle_wifi(state: bool):
    if not _ensure_device():
        return {"status": "error", "message": "No device"}
    out = _run([ADB, "shell", "svc", "wifi", "enable" if state else "disable"])
    return {"status": "success" if out["ok"] else "error", "message": "WiFi on" if state else "WiFi off", "stderr": out["stderr"]}

def toggle_bluetooth(state: bool):
    if not _ensure_device():
        return {"status": "error", "message": "No device"}
    if state:
        out = _run([ADB, "shell", "am", "start", "-a", "android.bluetooth.adapter.action.REQUEST_ENABLE"])
    else:
        out = _run([ADB, "shell", "am", "start", "-a", "android.bluetooth.adapter.action.REQUEST_DISABLE"])
    return {"status": "success" if out["ok"] else "error", "message": "Bluetooth on" if state else "Bluetooth off", "stderr": out["stderr"]}

def set_volume(level: int):
    if not _ensure_device():
        return {"status": "error", "message": "No device"}
    level = max(0, min(15, int(level)))
    out = _run([ADB, "shell", "media", "volume", "--stream", "3", "--set", str(level)])
    if not out["ok"]:
        for _ in range(16):
            _run([ADB, "shell", "input", "keyevent", "25"])
        for _ in range(level):
            _run([ADB, "shell", "input", "keyevent", "24"])
    return {"status": "success", "message": f"Volume set {level}/15"}

def toggle_airplane_mode(state: bool):
    if not _ensure_device():
        return {"status": "error", "message": "No device"}
    mode = "1" if state else "0"
    _run([ADB, "shell", "settings", "put", "global", "airplane_mode_on", mode])
    out = _run([ADB, "shell", "am", "broadcast", "-a", "android.intent.action.AIRPLANE_MODE"])
    return {"status": "success" if out["ok"] else "error", "message": "Airplane ON" if state else "Airplane OFF", "stderr": out["stderr"]}

def toggle_flashlight(state: bool):
    if not _ensure_device():
        return {"status": "error", "message": "No device"}
    action = "on" if state else "off"
    out = _run([ADB, "shell", "cmd", "torch", action])
    if not out["ok"]:
        # Fallback: prova intent rapido via camera tile (affidabilità dipende dal device)
        _run([ADB, "shell", "cmd", "statusbar", "expand-settings"])
        time.sleep(0.5)
    return {"status": "success" if out["ok"] else "error", "message": f"Torch {action}", "stderr": out["stderr"]}

def take_screenshot():
    if not _ensure_device():
        return {"status": "error", "message": "No device"}
    ts = int(time.time())
    remote = f"/sdcard/Download/jarvis_screenshot_{ts}.png"
    out = _run([ADB, "shell", "screencap", "-p", remote])
    return {"status": "success" if out["ok"] else "error", "path": remote, "stderr": out["stderr"]}

def record_screen(duration_sec: int = 30):
    if not _ensure_device():
        return {"status": "error", "message": "No device"}
    duration_sec = max(1, min(180, int(duration_sec)))
    ts = int(time.time())
    remote = f"/sdcard/Download/jarvis_record_{ts}.mp4"
    out = _run([ADB, "shell", "screenrecord", "--time-limit", str(duration_sec), remote], timeout=duration_sec + 5)
    return {"status": "success" if out["ok"] else "error", "path": remote, "stderr": out["stderr"]}

def get_notifications():
    if not _ensure_device():
        return {"status": "error", "message": "No device"}
    out = _run([ADB, "shell", "dumpsys", "notification"])
    lines = [l.strip() for l in out["stdout"].splitlines() if "NotificationRecord" in l][:10]
    return {"status": "success", "notifications": lines}

def send_sms(phone: str, message: str):
    if not _ensure_device():
        return {"status": "error", "message": "No device"}
    out = _run([ADB, "shell", "am", "start", "-a", "android.intent.action.SENDTO", "-d", f"sms:{phone}", "--es", "sms_body", message, "--ez", "exit_on_sent", "true"])
    return {"status": "success" if out["ok"] else "error", "message": f"SMS compose to {phone}", "note": "May require user tap Send"}

def send_whatsapp(phone: str, message: str):
    if not _ensure_device():
        return {"status": "error", "message": "No device"}
    wa = f"https://wa.me/{phone}?text=" + message.replace(" ", "%20")
    out = _run([ADB, "shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", wa])
    return {"status": "success" if out["ok"] else "error", "message": f"WhatsApp compose to {phone}", "note": "Requires user confirmation"}

def make_call(phone: str):
    if not _ensure_device():
        return {"status": "error", "message": "No device"}
    out = _run([ADB, "shell", "am", "start", "-a", "android.intent.action.CALL", "-d", f"tel:{phone}"])
    return {"status": "success" if out["ok"] else "error", "message": f"Calling {phone}"}

def end_call():
    if not _ensure_device():
        return {"status": "error", "message": "No device"}
    out = _run([ADB, "shell", "input", "keyevent", "KEYCODE_ENDCALL"])
    return {"status": "success" if out["ok"] else "error", "message": "Call ended"}

def camera_shot():
    if not _ensure_device():
        return {"status": "error", "message": "No device"}
    _run([ADB, "shell", "am", "start", "-a", "android.media.action.STILL_IMAGE_CAMERA"])
    time.sleep(1.0)
    out = _run([ADB, "shell", "input", "keyevent", "KEYCODE_CAMERA"])
    return {"status": "success" if out["ok"] else "error", "message": "Photo attempted"}
