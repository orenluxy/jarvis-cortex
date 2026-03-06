#!/bin/bash

# Ensure we are in the skill directory
cd "$(dirname "$0")" || exit 1

echo "🧠 Installing Jarvis Cortex dependencies (Lightweight)..."

# Check for pip
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 could not be found. Please install python3-pip."
    exit 1
fi

# Install ONLY requests (lightweight) and numpy (math)
# Removed google-generativeai to prevent OOM
pip3 install requests numpy --user --break-system-packages

# Create assets directory if not exists
mkdir -p ../assets

echo "✅ Dependencies installed (Lightweight Mode)."

# Ask user if they want to run ingest now
echo ""
echo "❓ Do you want to run the initial memory ingestion now?"
echo "   (This requires GOOGLE_API_KEY or OPENAI_API_KEY)"
read -p "   Run ingest? [y/N] " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ -z "$GOOGLE_API_KEY" ] && [ -z "$OPENAI_API_KEY" ]; then
        echo "❌ No API Key found. Set GOOGLE_API_KEY or OPENAI_API_KEY."
    else
        echo "🚀 Starting ingestion..."
        ./scripts/cortex.py ingest
    fi
else
    echo "ℹ️  Skipping ingestion. Run './scripts/cortex.py ingest' when you are ready."
fi

echo "✨ Installation complete."
