#!/bin/bash

# Ensure environment variables are set for cryptography
export CRYPTOGRAPHY_DONT_BUILD_RUST=1
export CRYPTOGRAPHY_USE_PURE_PYTHON=1

echo "Installing dependencies with PyO3 fix..."
echo "CRYPTOGRAPHY_DONT_BUILD_RUST=$CRYPTOGRAPHY_DONT_BUILD_RUST"
echo "CRYPTOGRAPHY_USE_PURE_PYTHON=$CRYPTOGRAPHY_USE_PURE_PYTHON"

# Install dependencies
pip3 install -r requirements.txt

echo "Dependencies installed successfully!" 