#!/usr/bin/env python
# check_config.py - Check current configuration values

import os
import sys
from dotenv import load_dotenv

# Load environment variables
print("Loading .env file...")
load_dotenv('.env')
print("Loading botex.env file...")
load_dotenv('botex.env')

# Check critical environment variables
critical_vars = [
    'OTREE_REST_KEY',
    'OTREE_ADMIN_PASSWORD',
    'OTREE_AUTH_LEVEL',
    'OTREE_SECRET_KEY',
    'OTREE_PRODUCTION',
    'BOTEX_DB',
    'OTREE_SERVER_URL',
]

print("\n=== Current Environment Configuration ===\n")

for var in critical_vars:
    value = os.environ.get(var)
    if value:
        if 'KEY' in var or 'PASSWORD' in var:
            # Partially hide sensitive information
            display_value = value[:5] + '...' + value[-5:] if len(value) > 10 else '***'
        else:
            display_value = value
        print(f"{var}: {display_value}")
    else:
        print(f"{var}: NOT SET")

print("\n=== Checking oTree Server ===\n")

# Try to check oTree server status
import requests

otree_url = os.environ.get('OTREE_SERVER_URL', 'http://localhost:8000')
print(f"Checking oTree server at: {otree_url}")

try:
    response = requests.get(f"{otree_url}/")
    print(f"Server response: {response.status_code}")
except Exception as e:
    print(f"Error connecting to server: {e}")

# Try to check API endpoint
rest_key = os.environ.get('OTREE_REST_KEY', '')
api_url = f"{otree_url}/api/sessions"

print(f"\nChecking API endpoint: {api_url}")
print(f"REST key available: {'Yes' if rest_key else 'No'}")

if rest_key:
    headers = {'otree-rest-key': rest_key}
    try:
        response = requests.get(api_url, headers=headers)
        print(f"API response: {response.status_code}")
        if response.status_code != 200:
            print(f"Response text: {response.text}")
    except Exception as e:
        print(f"Error connecting to API: {e}")
else:
    print("No REST key available, skipping API test")

print("\n=== Checking llama.cpp Server ===\n")

llama_url = "http://localhost:8080"
print(f"Checking llama.cpp server at: {llama_url}")

try:
    response = requests.get(f"{llama_url}/v1/models")
    print(f"Server response: {response.status_code}")
    if response.status_code == 200:
        print(f"Models available: {response.json()}")
except Exception as e:
    print(f"Error connecting to llama.cpp server: {e}")