#!/bin/bash

echo "Fixing Google Sheets authentication issues without cryptography..."

# Remove existing virtual environment if it exists
if [ -d "venv" ]; then
    echo "Removing existing virtual environment..."
    rm -rf venv
fi

# Create new virtual environment
echo "Creating new virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies with specific order to prevent conflicts (no cryptography)
echo "Installing dependencies..."
pip install protobuf==4.25.1
pip install google-auth==2.40.3
pip install google-auth-oauthlib==1.2.2
pip install google-auth-httplib2==0.2.0
pip install google-api-python-client==2.176.0

# Install remaining dependencies
pip install -r requirements.txt

echo "Dependencies installed successfully without cryptography!"
echo "To activate the environment, run: source venv/bin/activate"
echo "To test authentication, run: python test_google_auth.py" 