#!/bin/bash
set -e

echo "=== AdDigest — Desktop App Builder ==="

# Activate venv
source venv/bin/activate

# Install build deps
pip install -q pyinstaller pystray pillow

# Clean previous build
rm -rf build dist

# Build
pyinstaller AdDigest.spec --noconfirm

# Copy .env and credentials into the app's data folder
echo ""
echo "=== Copying config files ==="
APP_DATA="dist/AdDigest.app/Contents/MacOS"
cp .env "$APP_DATA/.env" 2>/dev/null || echo "Warning: .env not found — boss must add it manually"
cp coherent-brand-*.json "$APP_DATA/" 2>/dev/null || echo "Warning: service account JSON not found"

echo ""
echo "=== Done! ==="
echo "App is at: dist/AdDigest.app"
echo ""
echo "To distribute:"
echo "  1. Zip it:  cd dist && zip -r AdDigest.zip AdDigest.app"
echo "  2. Send the zip to your boss"
echo "  3. Boss: unzip → double-click AdDigest.app → browser opens automatically"
