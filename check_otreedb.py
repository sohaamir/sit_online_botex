# check_otree_db.py
import os
import sys
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')

import django
django.setup()

from otree.database import db

print(f"Database type: {type(db)}")
print(f"Database object: {db}")
print(f"Database _db attribute: {getattr(db, '_db', 'Not found')}")

# Check if database is initialized
try:
    from otree.models import Session
    sessions = Session.objects.all()
    print(f"Can access sessions: {len(sessions)} sessions found")
except Exception as e:
    print(f"Error accessing sessions: {e}")