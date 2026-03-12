#!/bin/bash
set -e

echo "======================================="
echo "  OpenTrace - Server Setup"
echo "======================================="
echo

# Check Python 3.10+
if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found. Install it with:"
    echo "  sudo apt install python3 python3-venv python3-pip"
    exit 1
fi

PYVER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYMINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')
if [ "$(python3 -c 'import sys; print(sys.version_info.major)')" -lt 3 ] || [ "$PYMINOR" -lt 10 ]; then
    echo "ERROR: Python 3.10+ required (found $PYVER)"
    exit 1
fi

echo "Python $PYVER found."
echo

echo "Creating virtual environment..."
python3 -m venv venv

echo "Installing dependencies..."
venv/bin/pip install --upgrade pip -q
venv/bin/pip install -r requirements.txt

echo
echo "Done! Next steps:"
echo "  1. Edit opentrace.service — set User and WorkingDirectory to match your setup"
echo "  2. sudo cp opentrace.service /etc/systemd/system/"
echo "  3. sudo systemctl enable --now opentrace"
echo "  4. Point your cloudflared tunnel at http://127.0.0.1:8000"
