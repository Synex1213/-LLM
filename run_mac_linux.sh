#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export NO_PROXY="${NO_PROXY:-},localhost,127.0.0.1"
export no_proxy="$NO_PROXY"
if [ ! -d .venv ]; then python3 -m venv .venv; fi
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
