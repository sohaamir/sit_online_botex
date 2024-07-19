# -------------------------------------------------------------------------------------------------------------------- #
# -------------------------- SETTINGS FOR THE OTREE APP HOSTED ON HEROKU ----------------------------- #
# -------------------------------------------------------------------------------------------------------------------- #

# This file contains the settings for the oTree application. These settings control the behavior of the app.
# You can customize these settings to fit your experiment. For more information, see the oTree documentation:
# https://otree.readthedocs.io/en/latest/

# LOAD DEPENDENCIES AND ENVIRONMENT VARIABLES
# ----------------------------------------------------------------
import os
from os import environ
from dotenv import load_dotenv

# Load environment variables from .env file
# This allows us to keep sensitive information out of the codebase
load_dotenv()

# SECURITY SETTINGS
# ----------------------------------------------------------------
# Secret key for cryptographic signing. This is critical for security.
# In production, this should be a long, random string stored as an environment variable.
SECRET_KEY = os.environ.get('OTREE_SECRET_KEY')

# Debug mode. This should be False in production to avoid exposing sensitive information.
# We set it to True if OTREE_PRODUCTION is not set to '1' in the environment.
DEBUG = os.environ.get('OTREE_PRODUCTION') != '1'

# Allowed hosts for the application. This is a security measure to prevent HTTP Host header attacks.
# In development, we allow localhost and 127.0.0.1. In production, add your domain name.
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '.herokuapp.com']

# Admin credentials. The username is hardcoded, but the password should be an environment variable.
# These credentials are used to access the oTree admin interface.
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = environ.get('OTREE_ADMIN_PASSWORD')

# OTREE-SPECIFIC SETTINGS
# ----------------------------------------------------------------
# Flag to indicate production environment. This affects various oTree behaviors.
OTREE_PRODUCTION = os.environ.get('OTREE_PRODUCTION') == '1'

# Custom fields for storing data at the participant and session level.
# These allow you to store additional data not covered by oTree's default fields.
PARTICIPANT_FIELDS = ['finished']
SESSION_FIELDS = []

# Use points instead of cash rewards.
USE_POINTS = True
# Custom name for points, displayed to participants.
# POINTS_CUSTOM_NAME = 'tokens'

# Browser bot configuration for automated testing.
# These bots can run through your experiment to check for errors.
BOTS_CHECK_HTML = False
BOTS_CHECK_COMPLETE = False

# SESSION CONFIGURATION
# ----------------------------------------------------------------
# Define the experimental session(s) for your oTree project.
# Each item in this list represents a different experiment or configuration.
SESSION_CONFIGS = [
     dict(
         name='social_influence_task',  # Unique identifier for this session configuration
         app_sequence=['main_task'],  # Order of apps in the experiment
         num_demo_participants=5,  # Number of demo participants, useful for testing
         # use_browser_bots=True,  # Uncomment to use bots for testing
         # Prolific completion links for different scenarios
         completionlink='https://bhampsychology.eu.qualtrics.com/jfe/form/SV_78qlaEMwYhSyUui', # Send to Qualtrics survey if participant completes the task
         noconsentlink='https://app.prolific.com/submissions/complete?cc=CDVJRJBR', # Send to Prolific if participant does not consent
         playerleftlink='https://app.prolific.com/submissions/complete?cc=CXG9SKDC', # End the task and send to Prolific if a participant leaves mid-task
         waitpagelink='https://app.prolific.com/submissions/complete?cc=C1J67YK4', # Send to Prolific if participant decides to leave the task
     ),
]

# Default configuration for all sessions.
# These settings apply to all sessions unless overridden in the specific session config.
SESSION_CONFIG_DEFAULTS = dict(
    real_world_currency_per_point=0.00,  # Conversion rate from points to real currency
    participation_fee=0.00,  # Fixed fee for participating
    doc=""  # Documentation string
)

# ROOM CONFIGURATION
# ----------------------------------------------------------------
# Define rooms for your experiments. Rooms allow you to create persistent URLs for participants.
ROOMS = [
    dict(
        name='social_influence_task',  # Unique identifier for the room
        display_name='Social Influence Task',  # Name displayed to participants
        # participant_label_file='_rooms/social_influence_task.txt',  # Uncomment to use pre-set participant labels
        # use_secure_urls=True,  # Uncomment to use secure URLs
    ),
]

# LOCALIZATION SETTINGS
# ----------------------------------------------------------------
# Language code for this installation. This affects the language of the admin interface.
LANGUAGE_CODE = 'en'

# Currency code for real-world currency. This is used in oTree's money formatting.
REAL_WORLD_CURRENCY_CODE = 'GBP'

# STATIC FILES CONFIGURATION
# ----------------------------------------------------------------
# Base directory of the project. This is used to build paths for static files.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Directories where Django will look for static files.
# This is where you should put your CSS, JavaScript, and images.
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, '_static'),
]

# PROFILER SETTINGS
# ----------------------------------------------------------------
# Enable the profiler for performance analysis. This can help identify bottlenecks in your code.
USE_PROFILER = True

# MISCELLANEOUS SETTINGS
# ----------------------------------------------------------------
# HTML content for the demo page. This is displayed when accessed via demo mode.
DEMO_PAGE_INTRO_HTML = """ """

# Commented out AUTH_LEVEL setting. Uncomment and set to 'STUDY' to password-protect your site.
# AUTH_LEVEL = os.environ.get('OTREE_AUTH_LEVEL', 'DEMO')