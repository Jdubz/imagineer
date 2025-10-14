#!/usr/bin/env python3
"""
Regenerate Preview Images with Auto-Detected Trigger Words

This script regenerates preview images for all LoRAs using automatically
extracted trigger words from their filenames instead of generic prompts.

Usage:
    # Queue all previews via API (recommended - runs async)
    python scripts/regenerate_previews.py --queue

    # Generate locally (synchronous - slower)
    python scripts/regenerate_previews.py

    # Regenerate only for specific LoRAs
    python scripts/regenerate_previews.py --queue --lora devil_carnival-000001 --lora tarot
"""

import sys
import json
from pathlib import Path

# Import from generate_previews
sys.path.insert(0, str(Path(__file__).parent))
from generate_previews import main as generate_main


if __name__ == '__main__':
    # Override sys.argv to call generate_previews with proper args
    # This ensures all existing LoRAs get regenerated (not just missing)

    if '--help' in sys.argv or '-h' in sys.argv:
        print(__doc__)
        sys.exit(0)

    # Remove --missing-only if present (we want to regenerate ALL)
    sys.argv = [arg for arg in sys.argv if arg != '--missing-only']

    print("="*80)
    print("REGENERATING ALL PREVIEWS WITH AUTO-DETECTED TRIGGER WORDS")
    print("="*80)
    print()
    print("This will replace existing previews with new ones using")
    print("trigger words extracted from LoRA filenames.")
    print()
    print("To test trigger word extraction first:")
    print("  python scripts/test_trigger_words.py")
    print()
    print("="*80)
    print()

    # Call generate_previews main function
    sys.exit(generate_main())
