#!/usr/bin/env python3
"""
Test script to verify trigger word extraction from LoRA filenames

This script shows what prompts will be auto-generated for each LoRA.
"""

import sys
import json
from pathlib import Path

# Import from organize_loras
sys.path.insert(0, str(Path(__file__).parent))
from organize_loras import extract_trigger_words, BLUE, YELLOW, GREEN, RESET


def main():
    lora_base_dir = Path('/mnt/speedy/imagineer/models/lora')
    index_path = lora_base_dir / 'index.json'

    if not index_path.exists():
        print(f"Error: index.json not found")
        return 1

    # Load index
    with open(index_path, 'r') as f:
        index = json.load(f)

    print(f"{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}Testing Trigger Word Extraction{RESET}")
    print(f"{BLUE}{'='*80}{RESET}\n")

    print(f"{'Filename':<40} → {'Trigger Words':<30}\n")

    for folder_name, entry in sorted(index.items()):
        filename = entry['filename']
        trigger_words = extract_trigger_words(filename)

        print(f"{YELLOW}{filename:<40}{RESET} → {GREEN}{trigger_words}{RESET}")

    print(f"\n{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}These trigger words will be used for preview generation{RESET}")
    print(f"{BLUE}Full prompt format: '<trigger_words>, high quality, detailed, professional'{RESET}")
    print(f"{BLUE}{'='*80}{RESET}\n")

    return 0


if __name__ == '__main__':
    sys.exit(main())
