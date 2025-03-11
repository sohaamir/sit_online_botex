# Online Social Influence Task

## Table of Contents

- [Overview](#overview)
- [Repository Structure](#repository-structure)
- [Technical Details](#technical-details)
- [Key Features](#key-features)
- [Installation](#installation)
- [Deployment on Heroku](#deployment-on-heroku)
- [Local Development](#local-development)
- [Command Reference](#command-reference)
- [Contact](#contact)
- [License](#license)

## Overview

This repository contains an implementation of a social influence task experiment using oTree, a Python framework for running behavioral experiments. The experiment is designed to investigate how people make decisions in social contexts, particularly how their choices are influenced by others in a group.

The task is based on a reversal learning paradigm where participants must learn which of two images is more likely to give rewards, with the reward probabilities periodically switching. Participants make choices and place bets in a group of 5 players, with the ability to see other players' decisions. The experiment measures how social influence affects decision-making, confidence, and learning.

The experiment aligns with previous work in the field, specifically building on the methodology from Zhang & Glascher (2020) with some modifications to the reward contingencies and trial structure.

## Repository Structure

The repository is organized into several oTree apps, each handling a different phase of the experiment:

### Primary Apps

- **instructions**: Presents study information, consent form, and task instructions
- **practice_task**: A shortened 5-round version of the task for participant training
- **main_task**: The primary 60-round experimental task with real-time group interaction
- **submission**: Handles participant feedback and redirects to external survey

### Key Files

- `settings.py`: Configuration file for the oTree application
- `Procfile`: Configuration for Heroku deployment
- `requirements.txt`: Python dependencies
- `heroku_cheatsheet.md`: Reference guide for Heroku commands
- `reversal_sequence.csv`: Generated sequence of reward probabilities

### Static Assets

- `_static/`: Contains image assets used in the experiment
- `_templates/`: HTML templates for the experiment interface

## Technical Details

### Python Version

- Python 3.11

### Key Dependencies

- `otree 5.11.1`
- `psycopg2 2.9.9`
- `redis 4.0.0+`
- `websockets 10.1`

### Database

- SQLite (development)
- PostgreSQL (production on Heroku)

## Key Features

### Experimental Design

- **Reversal Learning**: Reward contingencies switch between images at predetermined points
- **Real-time Group Interaction**: 5 players make choices simultaneously
- **Two-stage Decision Process**: Initial choice/bet followed by opportunity to revise after seeing others' choices
- **Confidence Measures**: Betting mechanism to measure confidence in decisions
- **Automatic Backup Choices**: Computer-generated choices if participant fails to respond in time
- **Robust Disconnection Handling**: Automatic bot activation for disconnected players

### User Experience

- **Comprehensive Instructions**: Detailed explanations with visual examples
- **Practice Task**: 5-round practice with longer response windows (6 seconds vs. 3 seconds in main task)
- **Responsive Timers**: Synchronized timed phases for each decision point
- **Participant Matching**: Waiting room to form groups of 5 participants
- **Snake Game**: Entertainment during waiting periods
- **Detailed Feedback Collection**: Post-experiment questions about influence and strategy

## Installation

### Prerequisites

- Python 3.11
- Git
- Heroku CLI (for deployment)

### Local Setup

Clone the repository:

```bash
git clone [repository-url]
cd social-influence-task
```

Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file with required environment variables:

```
OTREE_SECRET_KEY=your_secret_key
OTREE_ADMIN_PASSWORD=your_admin_password
```

Initialize the database:

```bash
otree resetdb
```

Run the development server:

```bash
otree devserver
```

## Deployment on Heroku

The application is designed for deployment on Heroku, with ready configurations in place.

### Initial Setup

Install the Heroku CLI and log in:

```bash
heroku login
```

Create a new Heroku app:

```bash
heroku create your-app-name
```

Add PostgreSQL database:

```bash
heroku addons:create heroku-postgresql:hobby-dev
```

Add Redis for websocket support:

```bash
heroku addons:create heroku-redis:hobby-dev
```

Configure environment variables:

```bash
heroku config:set OTREE_PRODUCTION=1
heroku config:set OTREE_ADMIN_PASSWORD=your_secure_password
heroku config:set OTREE_SECRET_KEY=your_very_secure_secret_key
heroku config:set WEBSOCKET_TIMEOUT=300
```

### Deployment

Deploy your code:

```bash
git push heroku main
```

Reset the database:

```bash
heroku run "otree resetdb"
```

Turn off maintenance mode:

```bash
heroku maintenance:off
```

### Managing Your Deployment

Refer to `heroku_cheatsheet.md` for a comprehensive list of commands for managing your Heroku deployment, including:

- Checking logs
- Managing environment variables
- Handling database resets
- Rollback procedures

## Local Development

### Running Tests

The repository includes bot scripts for automated testing:

```bash
otree test instructions
otree test practice_task
otree test main_task
otree test submission
```

### Testing with Browser Bots

For automated testing of the full experimental flow:

```bash
otree browser_bots social_influence_task 5
```

### Testing Browser Bots on Heroku

```bash
otree browser_bots social_influence_task 5 --server-url=https://your-app-name.herokuapp.com
```

## Command Reference

For a detailed list of useful commands for managing the application, refer to the `heroku_cheatsheet.md` file included in the repository. Key commands include:

### Setting Up

```bash
heroku login
heroku maintenance:off --app your-app-name
```

### Making Changes

```bash
git add .
git commit -am "your message"
git push heroku main
heroku run "otree resetdb"
```

### Configuring

```bash
heroku config -a your-app-name
heroku config:set WEBSOCKET_TIMEOUT=300 -a your-app-name
heroku restart -a your-app-name
```

## Contact

If you have questions or issues regarding this project, please reach out via:

- **Email**: axs2210@bham.ac.uk
- **GitHub**: Create an issue in the repository

The project was developed by **Aamir Sohail**, working under the supervision of **Dr. Lei Zhang** and **Professor Patricia Lockwood** at the School of Psychology, University of Birmingham.

## License

This project is academic research code. For permission to use or adapt this code, please contact the author directly at `axs2210@bham.ac.uk`.
