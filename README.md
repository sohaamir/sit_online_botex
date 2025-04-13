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

## Contact

If you have questions or issues regarding this project, please reach out via:

- **Email**: axs2210@bham.ac.uk
- **GitHub**: Create an issue in the repository

The project was developed by **Aamir Sohail**, working under the supervision of **Dr. Lei Zhang** and **Professor Patricia Lockwood** at the School of Psychology, University of Birmingham.

## License

This project is academic research code. For permission to use or adapt this code, please contact the author directly at `axs2210@bham.ac.uk`.
