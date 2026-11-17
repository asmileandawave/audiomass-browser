#!/usr/bin/env bash
# Usage: ./run.sh [ROOT_DIR] [PORT]   (defaults: ~/workspace, 8765)
cd "$(dirname "$0")" && exec python3 server.py --root "${1:-$HOME/workspace}" --port "${2:-8765}"
