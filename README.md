# Online Social Influence Task using LLM bots


## Overview

This repository contains a specific implementation of the social influence task, modified to test LLM bots using the Python package `botex`.

## Installation

### Prerequisites

- Python 3.10
- Git
- Python packages (see `requirements.txt`)

### Local Setup

Clone the repository:

```bash
git clone sohaamir/sit_online
cd sit_online
```

Create and activate a virtual environment (on Mac):

```bash
python -m venv venv
source venv/bin/activate
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

(optional) Download the TinyLLaMA model

```bash
chmod +x download_model.sh
./download_model.sh
```
## Running experiments

You can run experiments using the command line interface:

'python run_experiment.py <name> <sessions> <llm>'

Arguments:

`name`: Name of the experiment (e.g., "social_influence_task")
`sessions`: Number of concurrent sessions to run
`llm`: LLM model to use (e.g., "`gemini/gemini-1.5-flash`" or "`tinyllama`")

Optional arguments:

`--model_path`: Path to local model file (for tinyllama)
`--api_key`: API key for cloud models (if not set in .env)
`--strategy`: Bot strategy to use (options: standard, risk_taking, social_follower)
`--output_dir`: Directory to store output data

### Examples

Run with Gemini model:
`python run_experiment.py social_influence_task 1 gemini/gemini-1.5-flash`

Run with local TinyLLaMA model:
`python run_experiment.py social_influence_task 1 tinyllama`

Run with Gemini model using risk-taking strategy:
`python run_experiment.py social_influence_task 2 gemini/gemini-1.5-flash --strategy risk_taking`

## Contact

If you have questions or issues regarding this project, please reach out via:

- **Email**: axs2210@bham.ac.uk
- **GitHub**: Create an issue in the repository

The project was developed by **Aamir Sohail**, working under the supervision of **Dr. Lei Zhang** and **Professor Patricia Lockwood** at the School of Psychology, University of Birmingham.

## License

This project is academic research code. For permission to use or adapt this code, please contact the author directly at `axs2210@bham.ac.uk`.
