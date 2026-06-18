#!/bin/bash
set -e

# Resolve the directory where this script is located
REPO_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$REPO_DIR"

echo "=========================================================="
echo "🪶 PocketRAG Unified Installer"
echo "=========================================================="

# 1. Verify python3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 is required but not found on your system."
    exit 1
fi

# 2. Bootstrap virtual environment if needed
cd mcp
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment in mcp/.venv..."
    python3 -m venv .venv
fi

echo "Installing package and dependencies..."
.venv/bin/pip install -q -e "."
.venv/bin/pip install -q requests pytest pytest-asyncio

# 3. Run the python installation script
.venv/bin/python scripts/install.py
