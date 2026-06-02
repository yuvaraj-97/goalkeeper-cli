#!/usr/bin/env bash
# GoalKeeper CLI Installer Script
set -e

echo "🥅 Installing GoalKeeper CLI..."

# Check Python3
if ! command -v python3 &>/dev/null; then
    echo "❌ Error: python3 is not installed. Please install Python 3.7+ first."
    exit 1
fi

# Clone or download codebase
INSTALL_DIR="$HOME/.goalkeeper-cli"
mkdir -p "$INSTALL_DIR"

echo "📥 Fetching Goalkeeper package..."
# Download standard source code structure to ~/.goalkeeper-cli/
# (In production, this downloads from the GitHub release/archive)
cp -r /home/trader/goalkeeper-package/* "$INSTALL_DIR/"

cd "$INSTALL_DIR"

# Install package locally for the current user
echo "⚙️ Building and installing goalkeeper-cli..."
python3 setup.py install --user

# Run installer script to register cron and hooks
echo "🔧 Configuring CLI integrations..."
~/.local/bin/goalkeeper install

# Automatically run setup wizard
~/.local/bin/goalkeeper --setup
