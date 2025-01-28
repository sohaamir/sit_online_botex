# Heroku Command Cheat Sheet

## Overview
This cheat sheet covers essential Heroku commands for managing applications, including app deployment, configuration, monitoring, and maintenance. These commands are particularly useful for deploying and managing oTree applications on Heroku.

## Commands

### Login and authentication
`heroku login` # Login to your heroku account

`heroku auth:whoami` # Get your heroku username if logged in

### App Management
`heroku apps` # List all your Heroku apps

`heroku apps:info` # Show detailed information about your app

`heroku open` # Open your app in a web browser

### Deployment
`git push heroku main` # Deploy your code to Heroku

`heroku restart` # Restart all dynos in your app

### Configuration
`heroku config` # Display all environment variables

`heroku config:set KEY=VALUE` # Set an environment variable

Examples:

```bash
heroku config:set OTREE_PRODUCTION=1
heroku config:set OTREE_ADMIN_PASSWORD=zX9$mP2pL7@qR8TvN2$
heroku config:set OTREE_SECRET_KEY=h8J3fT9mN7vX2cQ5qR6tY4wZ8bE3sL7dB1gH5jM2nB6vC9xF4
```

`heroku addons` # List all add-ons for your app

### Monitoring 
`heroku logs --tail` # Display recent logs and stream in real-time

`heroku ps` # List the dynos for your app

### Database
`heroku run "otree resetdb"` # Reset the database for an oTree application

### Maintenance
`heroku maintenance:on` # Enable maintenance mode

`heroku maintenance:off --app social-influence-task` # Disable maintenance mode

### Help
`heroku help` # Display a list of Heroku commands

### Release Management
`heroku releases` # List release history for your app

### oTree-specific commands
`otree test [app_name] [num_participants]` # Run oTree tests

Example: `otree test social_influence_task 50`

`otree test [app_name] [num_participants] --server-url=[url]` # Run oTree tests on a specific server

Example: `otree test main_task 10 --server-url=https://social-influence-task-e7974ebf1c60.herokuapp.com/`

## Commands for setting up and powering down Heroku

### Logging in
`heroku login` # login to Heroku CLI

`heroku maintenance:off --app social_influence_task` # turn off maintenance mode to run Postgres and Redis

### Making changes and commiting them

```bash
git status
git add .
git commit -am "your message"
git push heroku main
```
Then reset the oTree database (if using oTree)

`heroku run "otree resetdb"` # reset database after pushing changes to heroku

### Turning off
`heroku maintenance:on` # turn maintenance mode on when powering down

`heroku logout` # logout of heroku

## Changing Heroku configs

### Get config list
`heroku config -a social-influence-task`

### Change config (e.g., websockets timeout config)
`heroku config:set WEBSOCKET_TIMEOUT=300 -a social-influence-task`

### Restart dynos
`heroku restart -a social-influence-task`

### Reset the database
`heroku run "otree resetdb"`

### Unset config changes
`heroku config:unset WEBSOCKET_TIMEOUT -a social-influence-task`

### Go back to a version that works on Heroku
`heroku rollback vxxx`

Example: `heroku rollback v143`

## Running Browser Bots with oTree

This guide explains how to run browser bots both locally and on your Heroku app.
Doing so on Heroku assumes you have your oTree app set-up and the Heroku CLI installed. 

Not necessarily required (but recommended) is `dotenv`, for storing your local variables. 
You can install it on your local environment using `pip install python-dotenv`, and then creating a `.env` file. 
You just then need to import these into your `settings.py`:

```python
import os
from os import environ
from dotenv import load_dotenv

load_dotenv()
```

### Local Browser Bot Testing

Running browser bots locally is rather simple, the technical problem lies with having a tests.py within each app that actually works.

Once you have that, simply run:

`otree browser_bots your_app_name number_of_participants`

Example: `otree browser_bots social_influence_task 5`

### Browser Bot Testing on Heroku

#### 1. Environment Setup

a) Creating and storing the REST API Key

Create or modify your OTREE_REST_KEY. First generate and set it as a config in Heroku, and then store it in your .env.

Create and set the config in Heroku:
`heroku config:set OTREE_REST_KEY=$(openssl rand -hex 32) --app your-app-name`   

In .env:
`OTREE_REST_KEY=xxxxxxx`

b) Setting the configs in your `settings.py`

In your `settings.py`, set `use_browser_bots` to `True` (either comment out or set to `False` otherwise).

Example:

```python
SESSION_CONFIGS = [
   dict(
       # Required settings
       use_browser_bots=True,  # Must be True to use browser bots
   ),
]
```

Also set the following Config Vars in your settings.py:

```python
OTREE_PRODUCTION=1
OTREE_REST_KEY=your_secure_key
OTREE_AUTH_LEVEL=STUDY
BOTS_CHECK_HTML = True
BOTS_CHECK_COMPLETE = True
USE_BROWSER_BOTS = True
```

#### 2. Run Browser Bots on Heroku
You should now be able to run your browser bots on Heroku using the following command:

`otree browser_bots your-app-name number-of-bots --server-url=https://your-app-name.herokuapp.com`

Example: `otree browser_bots social_influence_task 5 --server-url=https://social-influence-task-e7974ebf1c60.herokuapp.com` # To run 5 bots