#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

if [ ! -d .venv ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate

.venv/bin/pip install -q nicegui litellm python-dotenv

if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env from .env.example — edit it with your API key before continuing."
    exit 1
fi

exec .venv/bin/python main.py
