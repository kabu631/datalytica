"""
Datalytica License Key Generator
Run this script on YOUR machine (developer machine) to generate keys for customers.
Usage:
  python keygen.py                    # generates a key for THIS machine
  python keygen.py --machine <id>     # generates a key for a specific machine ID
  python keygen.py --plan pro --expiry 2027-12-31
"""
import sys, os

# Add backend to path so we can import license_service
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'services'))

from services.license_service import get_machine_id, generate_key

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Datalytica License Key Generator")
    parser.add_argument("--machine", default=None, help="Machine ID to generate key for (defaults to THIS machine)")
    parser.add_argument("--plan",    default="pro",        help="License plan: free | pro | enterprise")
    parser.add_argument("--expiry",  default="2099-12-31", help="Expiry date: YYYY-MM-DD")
    args = parser.parse_args()

    machine_id = args.machine or get_machine_id()
    key = generate_key(machine_id, args.plan, args.expiry)

    print("=" * 60)
    print("  Datalytica License Key Generator")
    print("=" * 60)
    print(f"  Machine ID : {machine_id}")
    print(f"  Plan       : {args.plan}")
    print(f"  Expiry     : {args.expiry}")
    print("-" * 60)
    print(f"  LICENSE KEY: {key}")
    print("=" * 60)

if __name__ == "__main__":
    main()
