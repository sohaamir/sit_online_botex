import os
import sys
import logging
import asyncio
import warnings
import websockets
from os import environ
from dotenv import load_dotenv
from websockets.exceptions import ConnectionClosedError, WebSocketProtocolError

# Load environment variables from .env file
load_dotenv()

# Set AUTH_LEVEL when running in production mode (i.e. on Heroku)
# AUTH_LEVEL = os.environ.get('OTREE_AUTH_LEVEL', 'DEMO')

SESSION_CONFIGS = [
     dict(
         name='social_influence_task',
         app_sequence=['instructions', 'practice_task', 'main_task_instructions', 'waiting_room', 'main_task', 'player_left', 'submission'],
         num_demo_participants=5,
         # use_browser_bots=True,
         completionlink='https://app.prolific.com/submissions/complete?cc=CKMY5BJS',
         noconsentlink='https://app.prolific.com/submissions/complete?cc=CDVJRJBR',
         playerleftlink='https://app.prolific.com/submissions/complete?cc=CXG9SKDC',
         waitpagelink='https://app.prolific.com/submissions/complete?cc=C1J67YK4',
     ),
]

# if you set a property in SESSION_CONFIG_DEFAULTS, it will be inherited by all configs
# in SESSION_CONFIGS, except those that explicitly override it.
# the session config can be accessed from methods in your apps as self.session.config,
# e.g. self.session.config['participation_fee']

SESSION_CONFIG_DEFAULTS = dict(
    real_world_currency_per_point=0.00, 
    participation_fee=0.00, 
    doc=""
)

ROOMS = [
    dict(
        name='social_influence_task',
        display_name='Social Influence Task',
        # participant_label_file='_rooms/social_influence_task.txt',
        # use_secure_urls=True
    ),
]

PARTICIPANT_FIELDS = ['finished']
SESSION_FIELDS = []

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, '_static'),
]
USE_PROFILER = True

# ISO-639 code
# for example: de, fr, ja, ko, zh-hans
LANGUAGE_CODE = 'en'

# e.g. EUR, GBP, CNY, JPY
REAL_WORLD_CURRENCY_CODE = 'GBP'
USE_POINTS = True

ADMIN_USERNAME = 'admin'
# for security, best to set admin password in an environment variable
ADMIN_PASSWORD = environ.get('OTREE_ADMIN_PASSWORD')

DEMO_PAGE_INTRO_HTML = """ """

SECRET_KEY = '9296799347406'

# Add this at the end of your settings.py file
USE_POINTS = True
POINTS_CUSTOM_NAME = 'tokens'

# Browser bot configuration
BOTS_CHECK_HTML = False
BOTS_CHECK_COMPLETE = False

# remove the websockets error message from the terminal
def custom_websocket_error_handler(loop, context):
    exception = context.get('exception')
    message = context.get('message', '')
    
    ignored_exceptions = (
        OSError,
        ConnectionClosedError,
        WebSocketProtocolError,
        asyncio.CancelledError,
    )
    
    ignored_messages = (
        "[Errno 57] Socket is not connected",
        "task exception was never retrieved",
        "closing handshake failed",
        "Socket is not connected",
    )
    
    if isinstance(exception, ignored_exceptions) or any(msg in message for msg in ignored_messages):
        return
    
    # For other exceptions, use the default exception handler
    loop.default_exception_handler(context)

# Set up logging
logging.basicConfig(level=logging.ERROR)

# Disable oTree's built-in logging for websocket errors
logging.getLogger('websockets').setLevel(logging.CRITICAL)
logging.getLogger('asyncio').setLevel(logging.CRITICAL)
logging.getLogger('django.channels').setLevel(logging.CRITICAL)

# Set the custom error handler
loop = asyncio.get_event_loop()
loop.set_exception_handler(custom_websocket_error_handler)

# Suppress ResourceWarning
warnings.simplefilter("ignore", ResourceWarning)