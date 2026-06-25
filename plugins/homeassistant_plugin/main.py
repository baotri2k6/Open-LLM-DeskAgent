import os
import json
import asyncio
from pathlib import Path
from typing import Dict, Any

STATE_FILE = Path(__file__).resolve().parent / "simulated_states.json"

DEFAULT_DEVICES = {
    "light.living_room": {"name": "Đèn phòng khách", "state": "off", "attributes": {"brightness": 100}},
    "light.bedroom": {"name": "Đèn phòng ngủ", "state": "on", "attributes": {"brightness": 70}},
    "climate.air_conditioner": {"name": "Điều hòa", "state": "off", "attributes": {"temperature": 24}},
    "switch.smart_plug": {"name": "Ổ cắm thông minh", "state": "off", "attributes": {}},
    "lock.main_door": {"name": "Khóa cửa chính", "state": "locked", "attributes": {}},
    "media_player.smart_speaker": {"name": "Loa thông minh", "state": "idle", "attributes": {"volume": 50}}
}

def load_simulated_devices() -> Dict[str, Any]:
    if not STATE_FILE.exists():
        save_simulated_devices(DEFAULT_DEVICES)
        return DEFAULT_DEVICES
    try:
        with STATE_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return DEFAULT_DEVICES

def save_simulated_devices(devices: Dict[str, Any]):
    try:
        with STATE_FILE.open("w", encoding="utf-8") as f:
            json.dump(devices, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

def _hass_request(url: str, method: str = "GET", payload: Any = None) -> Any:
    import urllib.request
    token = os.getenv("HOMEASSISTANT_TOKEN")
    base_url = os.getenv("HOMEASSISTANT_URL")
    if not base_url or not token:
        raise ValueError("Home Assistant credentials not configured")
        
    full_url = f"{base_url.rstrip('/')}/api/{url.lstrip('/')}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        
    req = urllib.request.Request(full_url, headers=headers, data=data, method=method)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))

async def homeassistant_get_devices() -> dict:
    token = os.getenv("HOMEASSISTANT_TOKEN")
    base_url = os.getenv("HOMEASSISTANT_URL")
    
    if token and base_url:
        try:
            states = await asyncio.to_thread(_hass_request, "states")
            devices_info = []
            for item in states:
                entity_id = item.get("entity_id")
                if any(entity_id.startswith(prefix) for prefix in ["light.", "switch.", "climate.", "lock.", "media_player."]):
                    devices_info.append({
                        "entity_id": entity_id,
                        "name": item.get("attributes", {}).get("friendly_name", entity_id),
                        "state": item.get("state"),
                        "attributes": item.get("attributes", {})
                    })
            return {"success": True, "source": "Home Assistant API", "devices": devices_info}
        except Exception as e:
            return {"success": False, "error": f"Lỗi khi kết nối Home Assistant API: {e}"}
    else:
        devices = load_simulated_devices()
        devices_list = []
        for eid, info in devices.items():
            devices_list.append({
                "entity_id": eid,
                "name": info["name"],
                "state": info["state"],
                "attributes": info.get("attributes", {})
            })
        return {"success": True, "source": "Simulated Smart Home", "devices": devices_list}

async def homeassistant_control_device(entity_id: str, action: str, value: str = None) -> dict:
    token = os.getenv("HOMEASSISTANT_TOKEN")
    base_url = os.getenv("HOMEASSISTANT_URL")
    
    if token and base_url:
        try:
            domain = entity_id.split(".")[0]
            service = action
            if action in ["turn_on", "turn_off", "toggle"]:
                service_url = f"services/{domain}/{action}"
            elif action == "set_temperature" and domain == "climate":
                service_url = f"services/climate/set_temperature"
            elif action == "lock" and domain == "lock":
                service_url = f"services/lock/lock"
            elif action == "unlock" and domain == "lock":
                service_url = f"services/lock/unlock"
            else:
                service_url = f"services/{domain}/{action}"
                
            payload = {"entity_id": entity_id}
            if action == "set_temperature" and value:
                payload["temperature"] = float(value)
            elif action == "set_volume" and value:
                payload["volume_level"] = float(value)
                
            res = await asyncio.to_thread(_hass_request, service_url, "POST", payload)
            return {"success": True, "source": "Home Assistant API", "result": res}
        except Exception as e:
            return {"success": False, "error": f"Lỗi khi điều khiển thiết bị qua Home Assistant API: {e}"}
    else:
        devices = load_simulated_devices()
        if entity_id not in devices:
            return {"success": False, "error": f"Không tìm thấy thiết bị '{entity_id}' trong hệ thống giả lập."}
            
        device = devices[entity_id]
        
        if action == "turn_on":
            device["state"] = "on"
        elif action == "turn_off":
            device["state"] = "off"
        elif action == "toggle":
            device["state"] = "off" if device["state"] == "on" else "on"
        elif action == "set_temperature":
            if not value:
                return {"success": False, "error": "Thiếu giá trị nhiệt độ."}
            device["state"] = "on"
            device["attributes"]["temperature"] = float(value)
        elif action == "lock":
            device["state"] = "locked"
        elif action == "unlock":
            device["state"] = "unlocked"
        elif action == "set_volume":
            if not value:
                return {"success": False, "error": "Thiếu giá trị âm lượng."}
            device["attributes"]["volume"] = float(value)
        else:
            return {"success": False, "error": f"Hành động '{action}' không được hỗ trợ trong hệ thống giả lập."}
            
        devices[entity_id] = device
        save_simulated_devices(devices)
        
        return {
            "success": True, 
            "source": "Simulated Smart Home", 
            "message": f"Đã thực hiện '{action}' cho thiết bị {device['name']} ({entity_id}).", 
            "device": {
                "entity_id": entity_id,
                "name": device["name"],
                "state": device["state"],
                "attributes": device["attributes"]
            }
        }
