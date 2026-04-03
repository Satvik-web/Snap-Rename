#!/bin/bash
# Snap Rename macOS Service Helper
# This script is called by the Finder Quick Action

PROJECT_DIR="/Users/satvikrajnarayanan/Snap Rename/Python Version"
PYTHON="/Library/Frameworks/Python.framework/Versions/3.10/bin/python3"

# Log start
echo "Service started at $(date)" > /tmp/snaprename_service.log
echo "Input: $1" >> /tmp/snaprename_service.log

cd "$PROJECT_DIR"
if [ -n "$1" ]; then
    "$PYTHON" "main.py" --gui -d "$1" >> /tmp/snaprename_service.log 2>&1
else
    "$PYTHON" "main.py" --gui >> /tmp/snaprename_service.log 2>&1
fi
