#!/usr/bin/env python3
"""
MacroDroid Remote Alternative - Termux Client Node
Developed by Osman Gani
"""

import time
import json
import subprocess
import urllib.request
import threading

# আপনার Firebase Database URL ও Device ID
FIREBASE_DB_URL = "https://phone-rat-10a3d-default-rtdb.firebaseio.com"
DEVICE_ID = "android_device_01"

def run_cmd(args):
    try:
        res = subprocess.run(args, capture_output=True, text=True, timeout=10)
        return res.stdout.strip()
    except Exception as e:
        return ""

def patch_firebase(path, data):
    url = f"{FIREBASE_DB_URL}/{path}.json"
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='PATCH'
        )
        urllib.request.urlopen(req, timeout=8)
    except Exception as e:
        pass

def get_from_firebase(path):
    url = f"{FIREBASE_DB_URL}/{path}.json"
    try:
        with urllib.request.urlopen(url, timeout=8) as res:
            raw = res.read().decode('utf-8')
            return json.loads(raw) if raw and raw != "null" else None
    except Exception:
        return None

def execute_action(action, payload):
    print(f"\n[⚡ COMMAND RECEIVED] {action} => {payload}")
    result = "Success"
    try:
        if action == "torch":
            state = "on" if payload is True or str(payload).lower() in ["true", "1", "on"] else "off"
            run_cmd(["termux-torch", state])
            result = f"Torch turned {state}"
            
        elif action == "alarm":
            run_cmd(["termux-volume", "alarm", "15"])
            run_cmd(["termux-vibrate", "-d", "4000"])
            run_cmd(["termux-tts-speak", "Emergency siren alert triggered on device!"])
            result = "Siren alarm triggered"
            
        elif action == "stop_alarm":
            run_cmd(["termux-torch", "off"])
            run_cmd(["termux-vibrate", "-d", "100"])
            result = "Silenced"
            
        elif action == "speak":
            text = str(payload)
            run_cmd(["termux-tts-speak", text])
            result = f"Spoke: {text[:30]}"
            
        elif action == "notification":
            title = payload.get("title", "Alert") if isinstance(payload, dict) else "Alert"
            msg = payload.get("message", "Message") if isinstance(payload, dict) else str(payload)
            run_cmd(["termux-notification", "--title", title, "--content", msg])
            result = f"Notification: {title}"
            
        elif action == "toast":
            run_cmd(["termux-toast", "-s", str(payload)])
            result = "Toast shown"
            
        elif action == "set_volume":
            stream = payload.get("stream", "music") if isinstance(payload, dict) else "music"
            if stream == "media": stream = "music"
            pct = int(payload.get("level", 80)) if isinstance(payload, dict) else 80
            level = int((pct / 100.0) * 15)
            run_cmd(["termux-volume", stream, str(level)])
            result = f"Volume {stream} set to {level}/15"
            
        elif action == "clipboard_push":
            run_cmd(["termux-clipboard-set", str(payload)])
            result = "Clipboard updated"
            
        elif action == "lock":
            run_cmd(["termux-toast", "Lock Phone command received"])
            result = "Lock triggered"
            
    except Exception as e:
        result = f"Error: {e}"

    # ড্যাশবোর্ডে অ্যাকনলেজ পাঠানো
    patch_firebase(f"devices/{DEVICE_ID}/commands", {
        "status": "executed",
        "result": result,
        "executedAt": int(time.time() * 1000)
    })
    print(f"[✔ EXECUTED] {result}")

def telemetry_worker():
    """প্রতি ১০ সেকেন্ডে ফোনের ব্যাটারি ও স্ট্যাটাস পাঠায়"""
    while True:
        try:
            bat_json = run_cmd(["termux-battery-status"])
            bat = json.loads(bat_json) if bat_json else {}
            pct = bat.get("percentage", 85)
            plugged = bat.get("plugged", "UNPLUGGED") != "UNPLUGGED"

            patch_firebase(f"devices/{DEVICE_ID}/status", {
                "batteryLevel": pct,
                "isCharging": plugged,
                "networkType": "Termux Wi-Fi",
                "wifiSSID": "Active",
                "lastSeen": int(time.time() * 1000),
                "isOnline": True
            })
            clip = run_cmd(["termux-clipboard-get"])
            if clip:
                patch_firebase(f"devices/{DEVICE_ID}/clipboard", {"text": clip})
        except Exception:
            pass
        time.sleep(10)

def main():
    print("=" * 55)
    print("⚡ MacroDroid Alternative - Termux Client Active")
    print(f"📡 Device ID : {DEVICE_ID}")
    print(f"🔥 Firebase  : {FIREBASE_DB_URL}")
    print("=" * 55)
    
    # টেলিমেট্রি ব্যাকগ্রাউন্ড থ্রেডে শুরু
    threading.Thread(target=telemetry_worker, daemon=True).start()
    
    last_time = 0
    print("🚀 Listening for commands from Web Admin...")
    while True:
        try:
            cmd = get_from_firebase(f"devices/{DEVICE_ID}/commands")
            if cmd and cmd.get("status") == "pending":
                ts = cmd.get("timestamp", 0)
                if ts > last_time:
                    last_time = ts
                    execute_action(cmd.get("action"), cmd.get("payload"))
        except Exception:
            pass
        time.sleep(1.2)

if __name__ == "__main__":
    main()
