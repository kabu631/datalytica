"""
Generate a machine-specific license key for a customer.

Usage:
    cd backend
    python tools/keygen.py <machine_id> [plan] [days]

Arguments:
    machine_id  16-char hex from GET /api/license/machine-id (customer provides this)
    plan        License tier: basic | pro | enterprise  (default: pro)
    days        Days until expiry                       (default: 365)

Example:
    python tools/keygen.py a1b2c3d4e5f6a7b8 pro 365
"""
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.license_service import generate_key


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    machine_id = sys.argv[1]
    plan = sys.argv[2] if len(sys.argv) > 2 else "pro"
    days = int(sys.argv[3]) if len(sys.argv) > 3 else 365

    expiry = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
    key = generate_key(machine_id, plan, expiry)

    print(f"\nLicense Key\n{'='*60}")
    print(key)
    print(f"{'='*60}")
    print(f"Machine : {machine_id}")
    print(f"Plan    : {plan}")
    print(f"Expiry  : {expiry}  ({days} days from today)")
    print("\nSend the key above to your customer.")


if __name__ == "__main__":
    main()
