#!/bin/bash

# Podcast Content Automation - Quick Setup Script
# This script automates the installation and setup process

set -e  # Exit on error

echo "🎙️ Podcast Content Automation - Setup"
echo "======================================"
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | grep -oP '\d+\.\d+')
if (( $(echo "$python_version < 3.8" | bc -l) )); then
    echo "❌ Error: Python 3.8 or higher required. Found: $python_version"
    exit 1
fi
echo "✅ Python $python_version detected"
echo ""

# Step 1: Install NotebookLM MCP
echo "Step 1: Installing NotebookLM MCP Server..."
if command -v uv &> /dev/null; then
    echo "Using uv..."
    uv tool install notebooklm-mcp-server
elif command -v pipx &> /dev/null; then
    echo "Using pipx..."
    pipx install notebooklm-mcp-server
else
    echo "Using pip..."
    pip install notebooklm-mcp-server
fi
echo "✅ NotebookLM MCP installed"
echo ""

# Step 2: Authenticate with NotebookLM
echo "Step 2: Authenticating with NotebookLM..."
echo "This will open Chrome for you to log in to Google."
read -p "Press Enter to continue..."
notebooklm-mcp-auth
echo "✅ Authentication complete"
echo ""

# Step 3: Create virtual environment
echo "Step 3: Setting up Python environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "ℹ️  Virtual environment already exists"
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
echo "✅ Dependencies installed"
echo ""

# Step 4: Google Drive setup (optional)
echo "Step 4: Google Drive Setup (Optional)"
echo "--------------------------------------"
echo "Do you want to set up Google Drive integration?"
echo "This allows automatic upload of generated content to Google Drive."
read -p "Setup Google Drive? (y/n): " setup_gdrive

if [ "$setup_gdrive" = "y" ] || [ "$setup_gdrive" = "Y" ]; then
    echo ""
    echo "To set up Google Drive:"
    echo "1. Go to https://console.cloud.google.com/"
    echo "2. Create a new project or select existing"
    echo "3. Enable Google Drive API"
    echo "4. Create OAuth 2.0 credentials (Desktop app)"
    echo "5. Download the credentials JSON file"
    echo ""
    read -p "Enter path to credentials JSON file: " creds_path
    
    if [ -f "$creds_path" ]; then
        mkdir -p ~/.podcast_automation
        cp "$creds_path" ~/.podcast_automation/credentials.json
        echo "✅ Credentials saved"
        
        # Create .env file
        cat > .env << EOF
GOOGLE_CREDENTIALS_PATH=$HOME/.podcast_automation/credentials.json
MCP_SERVER_URL=http://localhost:8000
EOF
        echo "✅ Environment configuration saved"
    else
        echo "⚠️  Credentials file not found. You can set this up later."
    fi
else
    echo "ℹ️  Skipping Google Drive setup"
fi

echo ""
echo "======================================"
echo "✅ Setup Complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo ""
echo "1. Start the NotebookLM MCP server in one terminal:"
echo "   notebooklm-mcp --transport http --port 8000"
echo ""
echo "2. In another terminal, activate the environment and run:"
echo "   source venv/bin/activate"
echo ""
echo "   Option A - Command Line:"
echo "   python podcast_to_content_automation.py 'EPISODE_URL' --name 'Episode Name'"
echo ""
echo "   Option B - Web Interface:"
echo "   python web_interface.py"
echo "   Then open http://localhost:5000 in your browser"
echo ""
echo "See README.md for detailed usage instructions."
echo ""
