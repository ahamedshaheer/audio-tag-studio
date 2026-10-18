#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR"

echo "========================================================"
echo "       Starting Audio Tag Studio & Cleaner...           "
echo "========================================================"

if command -v python3 &>/dev/null; then
    python3 server.py
elif command -v python &>/dev/null; then
    python server.py
else
    echo "[ERROR] Python 3 was not found in PATH."
    echo "Please install Python 3.8+."
    exit 1
fi
