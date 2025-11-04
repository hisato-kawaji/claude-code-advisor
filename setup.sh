#!/bin/bash

echo "Claude Code Analytics - Setup Script"
echo "===================================="
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo ""
    echo "Please edit .env file and add your ANTHROPIC_API_KEY"
    echo "Then run this script again."
    exit 1
fi

# Check if ANTHROPIC_API_KEY is set
source .env
if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "your_api_key_here" ]; then
    echo "Error: OPENAI_API_KEY is not set in .env file"
    echo "Please edit .env and add your API key"
    exit 1
fi

# Create data directory
mkdir -p data

echo "Building Docker containers..."
docker-compose build

echo ""
echo "Setup complete!"
echo ""
echo "To start the application, run:"
echo "  docker-compose up -d"
echo ""
echo "Then access the dashboard at:"
echo "  http://localhost:3000"
echo ""
echo "API documentation will be available at:"
echo "  http://localhost:8000/docs"
