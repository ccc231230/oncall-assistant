#!/bin/bash
set -e

echo "Starting On-Call Assistant..."
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
