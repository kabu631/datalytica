import requests

BASE = 'http://127.0.0.1:8765'

print('=== Datalytica End-to-End Health Check ===')
print()

# 1. Health
try:
    r = requests.get(f'{BASE}/', timeout=3)
    print(f'[1] Health check:    {r.status_code} OK')
except Exception as e:
    print(f'[1] Backend not running: {e}')
    exit(1)

# 2. License status
r = requests.get(f'{BASE}/api/license/status', timeout=3)
data = r.json()
plan   = data.get('plan', 'N/A')
expiry = data.get('expiry', 'N/A')
valid  = data.get('valid', False)
status = 'LICENSED' if valid else 'UNLICENSED'
print(f'[2] License status:  {status}  Plan={plan}  Expiry={expiry}')

# 3. Machine ID
r = requests.get(f'{BASE}/api/license/machine-id', timeout=3)
print(f'[3] Machine ID:      {r.json()["machine_id"]}')

# 4. Datasets list (requires valid license)
r = requests.get(f'{BASE}/api/ingest/datasets', timeout=3)
if r.status_code == 200:
    ds = r.json()
    print(f'[4] Datasets:        {len(ds)} dataset(s) found')
else:
    print(f'[4] Datasets:        HTTP {r.status_code}')

print()
print('==========================================')
