"""
Run this once on your (admin) machine to bypass the license check.

    cd backend
    python tools/activate_admin.py

Creates ~/.datalytica/.admin with the HMAC token. The app will detect this
file and skip license validation entirely on this machine.
"""
import sys
import os

# Make sure we can import from backend/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.license_service import activate_admin, _ADMIN_FILE

activate_admin()
print(f"Admin mode activated. Token written to: {_ADMIN_FILE}")
print("The app will now run without requiring a license key on this machine.")
