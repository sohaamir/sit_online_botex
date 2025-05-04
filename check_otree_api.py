#!/usr/bin/env python
# test_otree_api.py - Test oTree API directly

import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env')
load_dotenv('botex.env')

# Get configuration
otree_url = os.environ.get('OTREE_SERVER_URL', 'http://localhost:8000')
rest_key = os.environ.get('OTREE_REST_KEY', '')

print(f"Testing oTree API at: {otree_url}")
print(f"REST key: {'*' * 10 if rest_key else 'NOT SET'}")

# Test basic connection
print("\n1. Testing basic connection...")
try:
    response = requests.get(f"{otree_url}/")
    print(f"   Status: {response.status_code}")
except Exception as e:
    print(f"   Error: {e}")

# Test session configs endpoint
print("\n2. Testing session configs endpoint...")
api_url = f"{otree_url}/api/session_configs"
headers = {'otree-rest-key': rest_key} if rest_key else {}

try:
    response = requests.get(api_url, headers=headers)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        configs = response.json()
        print(f"   Available configs: {[c['name'] for c in configs]}")
    else:
        print(f"   Error: {response.text}")
except Exception as e:
    print(f"   Error: {e}")

# Test sessions endpoint (GET)
print("\n3. Testing sessions endpoint (GET)...")
api_url = f"{otree_url}/api/sessions"

try:
    response = requests.get(api_url, headers=headers)
    print(f"   Status: {response.status_code}")
    if response.status_code != 200:
        print(f"   Error: {response.text}")
except Exception as e:
    print(f"   Error: {e}")

# Test creating a session
print("\n4. Testing session creation...")
api_url = f"{otree_url}/api/sessions"
session_data = {
    'session_config_name': 'social_influence_task',
    'num_participants': 5
}

print(f"   Payload: {json.dumps(session_data)}")

try:
    response = requests.post(api_url, json=session_data, headers=headers)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        session = response.json()
        print(f"   Session created: {session.get('code', 'Unknown code')}")
    else:
        print(f"   Error: {response.text}")
except Exception as e:
    print(f"   Error: {e}")
    import traceback
    traceback.print_exc()