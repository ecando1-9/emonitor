import psutil
import json
import time
import os
import platform
import socket
import GPUtil
import requests
from config import config_manager, DATA_DIR
from logger_setup import log
from datetime import datetime
import asyncio
import winsdk.windows.devices.geolocation as wdg

OUTPUT_DIR = os.path.join(DATA_DIR, "captures")

def get_device_name_and_time():
    try:
        device_name = config_manager.get_settings()["user"]["device_name"]
    except Exception:
        device_name = "My-Computer"
    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    return device_name, timestamp

def get_battery_info():
    try:
        battery = psutil.sensors_battery()
        if battery:
            return {
                "percentage": f"{battery.percent:.0f}%",
                "is_plugged_in": battery.power_plugged,
                "secs_left": f"~{battery.secsleft // 60} min" if battery.secsleft and battery.secsleft != psutil.POWER_TIME_UNLIMITED else "N/A (or charging)"
            }
    except Exception as e:
        log.warning(f"Could not get battery info: {e}")
    return "Not available"

def get_system_info():
    try:
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot_time
        return {
            "os": f"{platform.system()} {platform.release()}",
            "user": os.getlogin(),
            "uptime": str(uptime).split('.')[0]
        }
    except Exception as e:
        log.warning(f"Could not get system info: {e}")
    return "Not available"

def get_network_info():
    info = {
        "ip_address": "N/A",
        "data_sent": f"{psutil.net_io_counters().bytes_sent / (1024*1024):.2f} MB",
        "data_received": f"{psutil.net_io_counters().bytes_recv / (1024*1024):.2f} MB"
    }
    try:
        all_addrs = psutil.net_if_addrs()
        for interface_name, addrs in all_addrs.items():
            for addr in addrs:
                if addr.family == socket.AF_INET and not addr.address.startswith("127."):
                    info["ip_address"] = addr.address
                    return info
    except Exception as e:
        log.warning(f"Could not get local IP: {e}")
    return info

def get_temperature_info():
    temps = {"cpu": "N/A", "gpu": "N/A"}
    try:
        if hasattr(psutil, "sensors_temperatures"):
            cpu_temps = psutil.sensors_temperatures()
            if "coretemp" in cpu_temps:
                temps["cpu"] = f"{cpu_temps['coretemp'][0].current}°C"
    except Exception as e:
        log.warning(f"Could not get CPU temp: {e}")
    try:
        gpus = GPUtil.getGPUs()
        if gpus:
            temps["gpu"] = f"{gpus[0].temperature}°C"
    except Exception as e:
        log.warning(f"Could not get GPU temp: {e}")
    return temps

def get_ip_location_info():
    """Gets estimated location (City/Country) using external IP address. (FALLBACK)"""
    try:
        response = requests.get('https://ipapi.co/json/', timeout=3)
        if response.status_code == 200:
            data = response.json()
            return {
                "type": "IP Geolocation (Approximate)",
                "external_ip": data.get("ip"),
                "city": data.get("city"),
                "region": data.get("region"),
                "country": data.get("country_name"),
                "isp": data.get("org")
            }
        else:
            log.warning(f"Location API failed with status: {response.status_code}")
            return "API request failed"
    except Exception as e:
        log.warning(f"Could not get IP location (no internet?): {e}")
        return "Not available (or offline)"

async def _get_precise_coords_async(timeout_seconds=10):
    """Gets precise GPS coordinates from Windows Location Service with timeout."""
    try:
        locator = wdg.Geolocator()
        # Request high accuracy
        locator.desired_accuracy = wdg.PositionAccuracy.HIGH
        
        # Get position with timeout
        pos = await asyncio.wait_for(
            locator.get_geoposition_async(),
            timeout=timeout_seconds
        )
        return pos.coordinate
    except asyncio.TimeoutError:
        log.warning("Location request timed out. Windows Location Service may be slow or unavailable.")
        raise TimeoutError("Location request timed out")
    except Exception as e:
        log.error(f"Error in async location request: {e}")
        raise

def get_precise_location_info():
    """Gets precise Lat/Lon from Windows Location Service (uses WiFi/GPS)."""
    try:
        coords = asyncio.run(_get_precise_coords_async(timeout_seconds=10))
        
        # Validate coordinates
        if coords is None:
            raise ValueError("Location service returned None")
        
        lat = coords.latitude
        lon = coords.longitude
        accuracy = getattr(coords, 'accuracy', None)
        
        # Validate coordinate ranges
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            raise ValueError(f"Invalid coordinates: lat={lat}, lon={lon}")
        
        result = {
            "type": "Windows Location Service (Precise GPS/WiFi)",
            "latitude": lat,
            "longitude": lon,
            "accuracy_meters": accuracy if accuracy is not None else "Unknown"
        }
        
        # Add altitude if available
        if hasattr(coords, 'altitude') and coords.altitude is not None:
            result["altitude_meters"] = coords.altitude
        
        log.info(f"Successfully obtained precise location: {lat}, {lon} (accuracy: {accuracy}m)")
        return result
        
    except PermissionError as e:
        log.warning(f"Could not get precise location: Windows Location Permission is OFF. Error: {e}")
        return {
            "type": "Permission Denied",
            "error": "Windows Location Permission is OFF",
            "message": "Please enable location services in Windows Settings > Privacy > Location"
        }
    except TimeoutError:
        log.warning("Location request timed out after 10 seconds.")
        return {
            "type": "Timeout",
            "error": "Location request timed out",
            "message": "Windows Location Service did not respond in time"
        }
    except AttributeError as e:
        log.error(f"Windows Location Service API error: {e}")
        return {
            "type": "API Error",
            "error": str(e),
            "message": "Windows Location Service may not be available on this system"
        }
    except Exception as e:
        error_type = type(e).__name__
        log.error(f"Failed to get precise location ({error_type}): {e}")
        return {
            "type": "Error",
            "error": error_type,
            "message": str(e)
        }

def get_location_info_data():
    """Gets the best possible location data instantly."""
    log.info("Attempting to get location data...")
    
    # Try to get precise GPS location first
    location_data = get_precise_location_info()
    
    # Check if precise location failed (returns dict with "error" key or string error message)
    is_error = False
    if isinstance(location_data, dict):
        if "error" in location_data or location_data.get("type") in ["Permission Denied", "Timeout", "Error", "API Error"]:
            is_error = True
    elif isinstance(location_data, str):
        if any(keyword in location_data.lower() for keyword in ["permission", "denied", "not available", "error", "timeout", "failed"]):
            is_error = True
    
    if is_error:
        log.warning("Precise GPS location failed. Falling back to IP Geolocation (approximate).")
        ip_location = get_ip_location_info()
        
        # If IP location also failed, return both attempts
        if isinstance(ip_location, str) and ("not available" in ip_location.lower() or "failed" in ip_location.lower()):
            return {
                "precise_gps_attempt": location_data,
                "ip_geolocation_attempt": ip_location,
                "status": "Both location methods failed"
            }
        
        # Return both: the failed precise attempt and the IP fallback
        return {
            "precise_gps_attempt": location_data,
            "ip_geolocation_fallback": ip_location,
            "note": "Precise GPS failed, using approximate IP-based location"
        }
    
    # Precise location succeeded
    log.info("Successfully obtained precise GPS location")
    return location_data

def capture_telemetry():
    """Captures advanced system telemetry and saves it to a JSON file"""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    try:
        device_name, timestamp = get_device_name_and_time()
        filename = os.path.join(OUTPUT_DIR, f"{device_name} - Telemetry - {timestamp}.json")
        data = {
            "timestamp": time.time(),
            "cpu_usage": f"{psutil.cpu_percent(interval=1)}%",
            "memory_usage": f"{psutil.virtual_memory().percent:.0f}%",
            "disk_usage": f"{psutil.disk_usage('/').percent:.0f}%",
            "battery_info": get_battery_info(),
            "network_info": get_network_info(),
            "temperature_info": get_temperature_info(),
            "location_info": get_location_info_data()
        }
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)
        log.info(f"Advanced Telemetry captured: {filename}")
        return filename
    except Exception as e:
        log.error(f"Error capturing advanced telemetry: {e}")
        return None