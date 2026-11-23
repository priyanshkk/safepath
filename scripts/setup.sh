#!/usr/bin/env bash
set -euo pipefail

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt

echo "Setup complete. Activate with: source .venv/bin/activate"
echo "Verify with: python -m unittest discover -s tests -v"
