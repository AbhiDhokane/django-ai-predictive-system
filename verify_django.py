"""
Verification test suite for Django AI Predictive Maintenance System.
"""
import os
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'predictive_maintenance.settings')
import django
django.setup()
from django.test import Client

client = Client()

tests = [
    ('GET', '/api/status', None),
    ('GET', '/api/machines', None),
    ('GET', '/api/readings/latest', None),
    ('GET', '/api/readings/history?machine_id=M01&limit=5', None),
    ('GET', '/api/overview', None),
    ('POST', '/api/predict', {'temperature': 85.0, 'vibration': 5.5, 'current': 9.5, 'rpm': 1100}),
    ('POST', '/api/readings', {'machine_id': 'M01', 'temperature': 62.1, 'vibration': 1.6, 'current': 4.9, 'rpm': 1630}),
    ('GET', '/api/alerts/recent', None),
    ('POST', '/api/simulator/tick', {}),
    ('POST', '/api/simulator/normalize?machine_id=M03', {}),
    ('GET', '/api/settings', None),
    ('POST', '/api/settings/email-toggle', {}),
    ('GET', '/', None),
    ('GET', '/style.css', None),
    ('GET', '/config.js', None),
    ('GET', '/app.js', None),
]

all_passed = True
print("=" * 65)
print("  Django AI Predictive Maintenance - System Verification")
print("=" * 65)

for method, url, body in tests:
    if method == 'GET':
        resp = client.get(url)
    else:
        resp = client.post(url, data=json.dumps(body) if body else '', content_type='application/json')
    
    is_ok = resp.status_code in (200, 201)
    status_str = "PASSED" if is_ok else f"FAILED ({resp.status_code})"
    print(f"{method:4s} {url:45s} -> {status_str}")
    if not is_ok:
        all_passed = False
        print(f"   [Error] {resp.content[:200]}")

print("=" * 65)
if all_passed:
    print("🎉 ALL 16 ENDPOINTS PASSED SUCCESSFULLY!")
else:
    print("❌ SOME TESTS FAILED!")
print("=" * 65)
