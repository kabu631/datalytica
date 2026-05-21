import hmac
import hashlib
import platform
import uuid
import base64
import json
import os
from datetime import datetime
from pathlib import Path
import sys as _sys
from dotenv import load_dotenv

if getattr(_sys, "frozen", False):
    _env_path = Path(_sys._MEIPASS) / "backend" / ".env"
else:
    _env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(_env_path)

SECRET = os.environ.get("DATALYTICA_SECRET")
if not SECRET:
    raise RuntimeError("DATALYTICA_SECRET environment variable is not set. Add it to backend/.env")

_ADMIN_FILE = Path.home() / ".datalytica" / ".admin"


def _admin_token() -> str:
    return hmac.new(SECRET.encode(), b"ADMIN_BYPASS_V1", hashlib.sha256).hexdigest()


def is_admin_mode() -> bool:
    """Return True if the admin token file exists and contains the correct hash."""
    try:
        return _ADMIN_FILE.read_text().strip() == _admin_token()
    except Exception:
        return False


def activate_admin() -> None:
    """Write the admin bypass token to disk. Call once on the developer's machine."""
    _ADMIN_FILE.parent.mkdir(parents=True, exist_ok=True)
    _ADMIN_FILE.write_text(_admin_token())


def get_machine_id() -> str:
    """Fingerprint: MAC address + platform + node name, hashed"""
    raw = f"{uuid.getnode()}-{platform.system()}-{platform.node()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]

def generate_key(machine_id: str, plan: str, expiry: str) -> str:
    """Generate a license key for a machine — run on your own machine"""
    payload = json.dumps({"m": machine_id, "p": plan, "e": expiry})
    sig = hmac.new(SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()[:16].upper()
    # Keep b64 as-is — base64 is case-sensitive, do NOT call .upper() on the whole key
    b64 = base64.urlsafe_b64encode(payload.encode()).decode().rstrip('=')
    return f"DL-{b64}-{sig}"

def validate_key(key: str) -> dict:
    """Validate key offline — no server required"""
    try:
        # Split on exactly the first and last '-' separator
        # Format: DL-<b64payload>-<16charSIG>
        if not key.startswith("DL-"):
            return {"valid": False, "error": "Invalid format"}

        # Signature is always the last 16 chars after the final '-'
        last_dash = key.rfind('-')
        sig_provided = key[last_dash + 1:].upper()
        b64 = key[3:last_dash]  # everything between "DL-" and the last "-"

        # Re-add base64 padding
        b64 += '=' * (-len(b64) % 4)

        payload = base64.urlsafe_b64decode(b64).decode()
        data = json.loads(payload)

        expected_sig = hmac.new(SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()[:16].upper()

        if not hmac.compare_digest(sig_provided, expected_sig):
            return {"valid": False, "error": "Invalid key signature"}

        if get_machine_id() != data['m']:
            return {"valid": False, "error": f"Wrong machine. Expected {data['m']}, got {get_machine_id()}"}

        if datetime.now().strftime('%Y-%m-%d') > data['e']:
            return {"valid": False, "error": "License expired"}

        return {"valid": True, "plan": data["p"], "expiry": data["e"]}

    except Exception as e:
        return {"valid": False, "error": str(e)}
