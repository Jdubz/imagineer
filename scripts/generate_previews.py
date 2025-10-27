#!/usr/bin/env python3
"""
Generate Preview Images for Organized LoRAs

Reads organized LoRAs from index.json and generates preview images.
Can run locally (synchronous) or queue jobs via API server (async).
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import yaml

# Import from organize_loras
sys.path.insert(0, str(Path(__file__).parent))
from organize_loras import (
    BLUE,
    GREEN,
    RED,
    RESET,
    YELLOW,
    extract_trigger_words,
    generate_preview,
    load_config,
    queue_preview_job,
    save_preview_config,
)

PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.yaml"


def main():
    parser = argparse.ArgumentParser(
        description="Generate preview images for organized LoRAs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Queue preview jobs via API server (recommended)
  python scripts/generate_previews.py --queue

  # Generate locally (synchronous, slower)
  python scripts/generate_previews.py

  # Regenerate only missing previews
  python scripts/generate_previews.py --missing-only

  # Generate for specific LoRA
  python scripts/generate_previews.py --lora t4r0th
        """,
    )

    parser.add_argument(
        "--lora-dir",
        default="/mnt/speedy/imagineer/models/lora",
        help="Base LoRA directory (default: /mnt/speedy/imagineer/models/lora)",
    )

    parser.add_argument(
        "--queue", action="store_true", help="Queue jobs via API server (requires server running)"
    )

    parser.add_argument(
        "--missing-only",
        action="store_true",
        help="Only generate previews for LoRAs without preview.png",
    )

    parser.add_argument("--lora", type=str, help="Generate preview for specific LoRA folder name")

    parser.add_argument(
        "--api-url",
        default="http://localhost:10050",
        help="API server URL (default: http://localhost:10050)",
    )

    args = parser.parse_args()

    lora_base_dir = Path(args.lora_dir)
    index_path = lora_base_dir / "index.json"

    if not lora_base_dir.exists():
        print(f"{RED}Error: LoRA directory not found: {lora_base_dir}{RESET}")
        return 1

    if not index_path.exists():
        print(f"{RED}Error: index.json not found. Run lora-organize first.{RESET}")
        return 1

    # Load index
    with open(index_path, "r") as f:
        index = json.load(f)

    # Load main config
    config_dict = load_config()
    if not config_dict:
        print(f"{YELLOW}Warning: Could not load config.yaml, using defaults{RESET}")
        negative_prompt = None
    else:
        negative_prompt = config_dict.get("generation", {}).get("negative_prompt")

    # Filter LoRAs to process
    loras_to_process = []

    if args.lora:
        # Specific LoRA
        if args.lora not in index:
            print(f"{RED}Error: LoRA '{args.lora}' not found in index{RESET}")
            return 1
        loras_to_process.append((args.lora, index[args.lora]))
    else:
        # All LoRAs
        for folder_name, entry in index.items():
            lora_folder = lora_base_dir / folder_name
            preview_path = lora_folder / "preview.png"

            # Skip if missing-only and preview exists
            if args.missing_only and preview_path.exists():
                continue

            loras_to_process.append((folder_name, entry))

    if not loras_to_process:
        print(f"{YELLOW}No LoRAs need preview generation{RESET}")
        return 0

    print(f"\n{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}Generating previews for {len(loras_to_process)} LoRA(s){RESET}")
    print(f"{BLUE}Mode: {'API Queue' if args.queue else 'Local (synchronous)'}{RESET}")
    print(f"{BLUE}{'='*80}{RESET}\n")

    success_count = 0
    failed_count = 0
    preview_config = None

    for folder_name, entry in loras_to_process:
        lora_folder = lora_base_dir / folder_name
        lora_file = lora_folder / entry["filename"]
        preview_path = lora_folder / "preview.png"

        if not lora_file.exists():
            print(f"{RED}✗ {folder_name}: LoRA file not found{RESET}")
            failed_count += 1
            continue

        print(f"{BLUE}{folder_name}{RESET}")
        print(f"  File: {entry['filename']}")

        # Auto-detect trigger words from filename
        trigger_words = extract_trigger_words(entry["filename"])
        print(f"  Trigger words: {YELLOW}{trigger_words}{RESET}")

        if args.queue:
            # Queue via API
            success, cfg = queue_preview_job(
                lora_file,
                preview_path,
                prompt=trigger_words,
                steps=30,
                guidance_scale=8.0,
                weight=1.0,
                negative_prompt=negative_prompt,
                api_url=args.api_url,
            )
        else:
            # Generate locally
            success, cfg = generate_preview(
                lora_file,
                preview_path,
                prompt=trigger_words,
                steps=30,
                guidance_scale=8.0,
                weight=1.0,
                negative_prompt=negative_prompt,
            )

        if success:
            success_count += 1
            if cfg:
                preview_config = cfg
        else:
            failed_count += 1

        print()

    # Save global preview config if we generated any
    if preview_config and not args.queue:
        save_preview_config(lora_base_dir, preview_config)
        print(f"{GREEN}✓ Preview config saved{RESET}")

    # Summary
    print(f"\n{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}Preview Generation Summary:{RESET}")
    print(f"  Total: {len(loras_to_process)}")
    print(f"  {GREEN}Success: {success_count}{RESET}")
    if failed_count > 0:
        print(f"  {RED}Failed: {failed_count}{RESET}")

    if args.queue:
        print(f"\n{YELLOW}Preview jobs queued. Monitor progress:{RESET}")
        print(f"  {BLUE}curl {args.api_url}/api/jobs{RESET}")

    print(f"{BLUE}{'='*80}{RESET}\n")

    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
