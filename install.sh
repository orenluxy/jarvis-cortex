#!/bin/bash

# Ensure we are in the skill directory
cd "$(dirname "$0")" || exit 1

echo "Installing Jarvis Cortex dependencies..."

# Check for pip
if ! command -v pip3 &> /dev/null; then
    echo "pip3 could not be found. Please install python3-pip."
    exit 1
fi

# Install python dependencies with --break-system-packages for managed environments
# This is safe for single-purpose skills
pip3 install google-generativeai numpy --user --break-system-packages

# Create assets directory if not exists
mkdir -p ../assets

echo "Installation complete."
echo "Please ensure GOOGLE_API_KEY environment variable is set in your shell or .env file."
