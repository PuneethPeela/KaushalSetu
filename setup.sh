#!/bin/bash
# ============================================================
# KAUSHALSETU — SETUP SCRIPT (Mac / Linux)
#
# What to do: open a terminal in this folder and run:
#     bash setup.sh
#
# This installs the two Python packages needed (pandas, numpy)
# and then builds + opens your dashboard automatically.
# ============================================================

echo "=========================================="
echo " KaushalSetu — Setup"
echo "=========================================="
echo ""
echo "[1/2] Installing required packages (pandas, numpy)..."
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo ""
    echo "pip failed. Trying pip3 instead..."
    pip3 install -r requirements.txt
fi

echo ""
echo "[2/2] Building your dashboard..."
python3 build_and_launch.py

if [ $? -ne 0 ]; then
    echo "python3 failed, trying 'python' instead..."
    python build_and_launch.py
fi
