#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "Initializing git repository..."
git init
git add .
git commit -m "init: project scaffold"

echo "Done. Repository initialized with initial commit."
