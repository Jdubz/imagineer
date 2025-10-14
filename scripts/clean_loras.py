#!/usr/bin/env python3
"""
LoRA Compatibility Checker & Cleaner

Inspects LoRA .safetensors files to detect incompatible formats:
- LyCORIS/Hadamard LoRAs (hada_* keys)
- SDXL LoRAs (wrong dimensions/architecture)
- Other incompatible formats

Compatible: Standard SD1.5 LoRAs with lora_up/lora_down keys
"""

import sys
from pathlib import Path
from safetensors import safe_open
from collections import defaultdict
import shutil

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def check_lora_compatibility(lora_path):
    """
    Check if a LoRA file is compatible with SD1.5
    
    Returns:
        tuple: (is_compatible, reason, details)
    """
    try:
        with safe_open(lora_path, framework="pt", device="cpu") as f:
            keys = list(f.keys())
            
            if not keys:
                return False, "empty", "No keys found in file"
            
            # Check for LyCORIS/Hadamard format
            lycoris_keys = [k for k in keys if 'hada_' in k]
            if lycoris_keys:
                return False, "lycoris", f"Found {len(lycoris_keys)} LyCORIS/Hadamard keys"
            
            # Check for LoKr format
            lokr_keys = [k for k in keys if 'lokr_' in k]
            if lokr_keys:
                return False, "lokr", f"Found {len(lokr_keys)} LoKr keys"
            
            # Check for standard LoRA keys
            lora_keys = [k for k in keys if '.lora_up.weight' in k or '.lora_down.weight' in k]

            if not lora_keys:
                return False, "unknown", f"No standard LoRA keys found (total keys: {len(keys)})"

            # Check for SDXL dual text encoder (lora_te1 or lora_te2)
            # SD 1.5 only has lora_te (single text encoder)
            te1_keys = [k for k in keys if 'lora_te1' in k or 'lora_te2' in k]
            if te1_keys:
                return False, "sdxl", f"Detected SDXL dual text encoder ({len(te1_keys)} te1/te2 keys)"

            # Check for Illustrious/SDXL-specific key patterns
            # These models use different module naming conventions
            illustrious_patterns = [
                'transformer_blocks.0.attn1.to_',
                'transformer_blocks.0.attn2.to_',
                'transformer_blocks.0.ff.net',
                '.proj_in',
                '.proj_out',
                'mid_block.1.transformer_blocks'
            ]

            # Look for these patterns in LoRA keys
            for pattern in illustrious_patterns:
                matching_keys = [k for k in keys if pattern in k]
                if matching_keys:
                    # Check if it's actually a numbered pattern like "0.1.transformer_blocks"
                    # which is characteristic of Illustrious/SDXL
                    numbered_pattern = any(k for k in matching_keys if '.1.transformer_blocks' in k or '.0.transformer_blocks' in k)
                    if numbered_pattern:
                        return False, "illustrious", f"Detected Illustrious/SDXL architecture (found {pattern} pattern)"

            # Check tensor dimensions to detect SDXL by size
            # SD1.5 UNet typically has smaller dimensions than SDXL
            # Sample a few keys to check dimensions
            sample_keys = [k for k in keys if 'lora_unet' in k and 'lora_down.weight' in k][:5]

            if sample_keys:
                max_dim = 0
                for key in sample_keys:
                    tensor = f.get_tensor(key)
                    max_dim = max(max_dim, max(tensor.shape))

                # SDXL LoRAs typically have dimensions > 2048 in UNet layers
                # SD1.5 LoRAs typically stay under 1280
                if max_dim > 2048:
                    return False, "sdxl", f"Detected SDXL dimensions (max: {max_dim})"

            # If we got here, it's likely a compatible SD1.5 LoRA
            return True, "sd15", f"Standard SD1.5 LoRA ({len(lora_keys)} LoRA keys)"
            
    except Exception as e:
        return False, "error", f"Failed to read: {str(e)}"


def format_size(size_bytes):
    """Format file size in human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f}TB"


def scan_lora_directory(base_dir, dry_run=True, move_incompatible=True):
    """
    Scan all LoRA directories and check compatibility
    
    Args:
        base_dir: Base LoRA directory path
        dry_run: If True, don't move files (just report)
        move_incompatible: If True, move incompatible files to _incompatible/
    """
    base_path = Path(base_dir)
    
    if not base_path.exists():
        print(f"{RED}Error: Directory not found: {base_dir}{RESET}")
        return
    
    # Find all set directories (exclude _incompatible)
    set_dirs = [d for d in base_path.iterdir() 
                if d.is_dir() and not d.name.startswith('_') and not d.name.startswith('.')]
    
    if not set_dirs:
        print(f"{YELLOW}No set directories found in {base_dir}{RESET}")
        return
    
    # Statistics
    stats = defaultdict(int)
    results = []
    
    print(f"\n{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}Scanning LoRA files...{RESET}")
    print(f"{BLUE}{'='*80}{RESET}\n")
    
    for set_dir in sorted(set_dirs):
        lora_files = list(set_dir.glob('*.safetensors'))
        
        if not lora_files:
            continue
        
        print(f"{BLUE}[{set_dir.name}]{RESET} - {len(lora_files)} file(s)")
        
        for lora_file in sorted(lora_files):
            file_size = lora_file.stat().st_size
            is_compatible, reason, details = check_lora_compatibility(lora_file)
            
            stats[reason] += 1
            
            result = {
                'file': lora_file,
                'set': set_dir.name,
                'compatible': is_compatible,
                'reason': reason,
                'details': details,
                'size': file_size
            }
            results.append(result)
            
            if is_compatible:
                print(f"  {GREEN}✓{RESET} {lora_file.name:<45} {format_size(file_size):>10} - {details}")
            else:
                print(f"  {RED}✗{RESET} {lora_file.name:<45} {format_size(file_size):>10} - {RED}{reason.upper()}{RESET}: {details}")
        
        print()
    
    # Summary
    print(f"\n{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}Summary{RESET}")
    print(f"{BLUE}{'='*80}{RESET}")
    print(f"  {GREEN}Compatible (SD1.5):{RESET} {stats['sd15']}")
    print(f"  {RED}Incompatible:{RESET}")
    print(f"    - LyCORIS/Hadamard: {stats['lycoris']}")
    print(f"    - LoKr: {stats['lokr']}")
    print(f"    - Illustrious/SDXL: {stats['illustrious']}")
    print(f"    - SDXL (dimensions): {stats['sdxl']}")
    print(f"    - Unknown format: {stats['unknown']}")
    print(f"    - Read errors: {stats['error']}")
    print(f"  {BLUE}Total:{RESET} {sum(stats.values())}")
    
    # Move incompatible files
    if move_incompatible and not dry_run:
        incompatible_files = [r for r in results if not r['compatible']]
        
        if incompatible_files:
            incompatible_dir = base_path / '_incompatible'
            incompatible_dir.mkdir(exist_ok=True)
            
            print(f"\n{YELLOW}Moving {len(incompatible_files)} incompatible file(s) to _incompatible/{RESET}")
            
            for result in incompatible_files:
                src = result['file']
                dst = incompatible_dir / f"{result['reason']}_{src.name}"
                
                try:
                    shutil.move(str(src), str(dst))
                    print(f"  {YELLOW}→{RESET} {src.name} → {dst.name}")
                except Exception as e:
                    print(f"  {RED}✗{RESET} Failed to move {src.name}: {e}")
            
            print(f"\n{GREEN}✓ Cleanup complete{RESET}")
    
    elif move_incompatible and dry_run:
        incompatible_count = sum(1 for r in results if not r['compatible'])
        if incompatible_count > 0:
            print(f"\n{YELLOW}Dry run mode: Would move {incompatible_count} incompatible file(s){RESET}")
            print(f"{YELLOW}Run with --clean to actually move files{RESET}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Check and clean incompatible LoRA files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check compatibility (dry run)
  python scripts/clean_loras.py

  # Actually move incompatible files
  python scripts/clean_loras.py --clean

  # Specify custom LoRA directory
  python scripts/clean_loras.py --lora-dir /path/to/loras
        """
    )
    
    parser.add_argument(
        '--lora-dir',
        default='/mnt/speedy/imagineer/models/lora',
        help='Base LoRA directory (default: /mnt/speedy/imagineer/models/lora)'
    )
    
    parser.add_argument(
        '--clean',
        action='store_true',
        help='Actually move incompatible files (default: dry run)'
    )
    
    parser.add_argument(
        '--no-move',
        action='store_true',
        help='Just report, don\'t move files even with --clean'
    )
    
    args = parser.parse_args()
    
    scan_lora_directory(
        args.lora_dir,
        dry_run=not args.clean,
        move_incompatible=not args.no_move
    )


if __name__ == '__main__':
    main()
