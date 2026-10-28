#!/bin/bash

echo "🚀 Setting up AI Data Analytics Agent..."

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies (runtime + test/lint tooling)
pip install --upgrade pip
pip install -r requirements-dev.txt

# Create .env from example if it doesn't exist
if [ ! -f .env ]; then
    cp .env.example .env
    echo "📝 Created .env file from template. Please edit with your API keys."
fi

echo "✅ Setup complete! Run 'source venv/bin/activate' to activate the environment."
