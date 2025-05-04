import os
import sys
import django
from dotenv import load_dotenv

# Load environment
load_dotenv('.env')
load_dotenv('botex.env')

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

# Import oTree's API utilities
from otree.api import call_api
import otree.session
import botex

# Create session using oTree's own API
try:
    print("Creating session using oTree's call_api...")
    
    # Use oTree's call_api function
    data = call_api(
        'POST',
        'sessions',
        session_config_name='social_influence_task',
        num_participants=5
    )
    
    session_code = data['code']
    print(f"Session created successfully: {session_code}")
    
    # Now run botex on this session
    print("Running botex on the session...")
    botex.run_single_bot(
        url=f"http://localhost:8000/InitializeParticipant/{data['participant_codes'][0]}",
        session_name='social_influence_task',
        session_id=session_code,
        participant_id=data['participant_codes'][0],
        botex_db='botex.sqlite3',
        model='llamacpp',
        api_base='http://localhost:8080'
    )
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()