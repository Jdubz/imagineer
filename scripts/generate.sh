#!/bin/bash
# Quick wrapper for image generation
cd "$(dirname "$0")/.."
source venv/bin/activate
python examples/generate.py "$@"
