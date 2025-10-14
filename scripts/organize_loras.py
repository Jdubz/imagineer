#!/usr/bin/env python3
"""
LoRA Organization & Preview Generator

Automatically organizes new LoRAs found in the root directory:
1. Tests compatibility (SD1.5 only)
2. Moves incompatible files to _incompatible/
3. Creates dedicated folder for each compatible LoRA
4. Generates preview image (640x640 with full weight)
5. Creates config file (name, weight, preview path)
6. Updates index file
7. Reconciles index against actual folders
"""

import sys
import json
import yaml
import subprocess
from pathlib import Path
from datetime import datetime
from safetensors import safe_open
from collections import defaultdict
import shutil
import re

# Import compatibility checker from clean_loras
sys.path.insert(0, str(Path(__file__).parent))
from clean_loras import check_lora_compatibility, format_size, GREEN, RED, YELLOW, BLUE, RESET

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
GENERATE_SCRIPT = PROJECT_ROOT / 'examples' / 'generate.py'
VENV_PYTHON = PROJECT_ROOT / 'venv' / 'bin' / 'python'
CONFIG_PATH = PROJECT_ROOT / 'config.yaml'


def load_config():
    """Load main config.yaml"""
    if not CONFIG_PATH.exists():
        return None

    try:
        with open(CONFIG_PATH, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"{RED}Error loading config: {e}{RESET}")
        return None


def sanitize_name(name):
    """Sanitize filename for folder name"""
    # Remove extension
    name = Path(name).stem
    # Replace spaces and special chars with underscores
    name = re.sub(r'[^\w\-]', '_', name)
    # Remove multiple underscores
    name = re.sub(r'_+', '_', name)
    # Strip leading/trailing underscores
    name = name.strip('_')
    return name.lower()


def extract_trigger_words(filename):
    """Extract likely trigger words from LoRA filename

    Converts filename into natural language prompt suitable for previews.
    Examples:
        Devil Carnival-000001.safetensors -> "devil carnival"
        Card_Fronts-000008.safetensors -> "card fronts"
        CelestialTarot_V2.safetensors -> "celestial tarot"

    Args:
        filename: LoRA filename (with or without extension)

    Returns:
        str: Extracted trigger words
    """
    # Remove extension
    name = Path(filename).stem

    # Remove version patterns: -000001, _V2, -v3, etc.
    name = re.sub(r'[-_]v?\d+$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'[-_]\d{6}$', '', name)  # Remove -000001 style

    # Replace underscores/hyphens with spaces
    name = name.replace('_', ' ').replace('-', ' ')

    # Split camelCase (e.g., CelestialTarot -> Celestial Tarot)
    name = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)

    # Clean up multiple spaces
    name = re.sub(r'\s+', ' ', name).strip()

    return name.lower()


def load_index(lora_base_dir):
    """Load the LoRA index file"""
    index_path = lora_base_dir / 'index.json'
    
    if not index_path.exists():
        return {}
    
    try:
        with open(index_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"{RED}Error loading index: {e}{RESET}")
        return {}


def save_preview_config(lora_base_dir, preview_config):
    """Save global preview config to separate file

    Args:
        lora_base_dir: Base directory path
        preview_config: Preview config dict to save
    """
    preview_config_path = lora_base_dir / 'preview_config.json'

    try:
        with open(preview_config_path, 'w') as f:
            json.dump(preview_config, f, indent=2)
        return True
    except Exception as e:
        print(f"{RED}Error saving preview config: {e}{RESET}")
        return False


def load_preview_config(lora_base_dir):
    """Load global preview config from separate file

    Returns default config if file doesn't exist
    """
    preview_config_path = lora_base_dir / 'preview_config.json'

    default_config = {
        'prompt': 'jester',
        'full_prompt': 'jester, high quality, detailed, professional',
        'width': 640,
        'height': 640,
        'steps': 30,
        'guidance_scale': 8.0,
        'weight': 1.0,
        'negative_prompt_source': 'config.yaml',
        'note': 'All previews use these settings for consistency'
    }

    if not preview_config_path.exists():
        return default_config

    try:
        with open(preview_config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"{YELLOW}Warning: Could not load preview_config.json: {e}{RESET}")
        return default_config


def save_index(lora_base_dir, index):
    """Save the LoRA index file

    Args:
        lora_base_dir: Base directory path
        index: Dict of LoRA entries
    """
    index_path = lora_base_dir / 'index.json'

    try:
        # Save index sorted by key for consistency
        sorted_index = {k: index[k] for k in sorted(index.keys())}

        with open(index_path, 'w') as f:
            json.dump(sorted_index, f, indent=2)
        return True
    except Exception as e:
        print(f"{RED}Error saving index: {e}{RESET}")
        return False


def create_lora_config(lora_folder, lora_file, preview_rel_path, default_weight=0.6):
    """Create config file for a LoRA"""
    config = {
        'name': lora_folder.name.replace('_', ' ').title(),
        'filename': lora_file.name,
        'default_weight': default_weight,
        'preview_image': preview_rel_path,
        'created': datetime.now().isoformat(),
        'compatible': 'sd15',
        'notes': 'TODO: Add description and recommended use cases'
    }
    
    config_path = lora_folder / 'config.yaml'
    
    try:
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        return True
    except Exception as e:
        print(f"{RED}Error creating config: {e}{RESET}")
        return False


def queue_preview_job(lora_path, output_path, prompt=None, width=640, height=640, steps=30, guidance_scale=8.0, weight=1.0, negative_prompt=None, api_url="http://localhost:10050"):
    """Queue a preview generation job via the API server

    Args:
        prompt: Custom prompt (if None, auto-extracts from filename)

    Returns:
        tuple: (success: bool, preview_config: dict)
    """
    import requests

    # Auto-extract trigger words from filename if no prompt provided
    if prompt is None:
        prompt = extract_trigger_words(lora_path.name)
        print(f"    {BLUE}Auto-detected prompt: '{prompt}'{RESET}")

    full_prompt = f"{prompt}, high quality, detailed, professional"

    # Store preview config for global storage
    preview_config = {
        'prompt': prompt,
        'full_prompt': full_prompt,
        'width': width,
        'height': height,
        'steps': steps,
        'guidance_scale': guidance_scale,
        'weight': weight,
        'negative_prompt_source': 'config.yaml' if negative_prompt else None,
        'negative_prompt_length': len(negative_prompt) if negative_prompt else 0,
        'note': 'All previews use these settings for consistency'
    }

    # Prepare job data
    job_data = {
        'prompt': full_prompt,
        'width': width,
        'height': height,
        'steps': steps,
        'guidance_scale': guidance_scale,
        'negative_prompt': negative_prompt,
        'lora_paths': [str(lora_path)],
        'lora_weights': [weight],
        'output': str(output_path)
    }

    try:
        print(f"    {BLUE}Queueing preview job...{RESET}", end='', flush=True)
        response = requests.post(
            f"{api_url}/api/generate",
            json=job_data,
            timeout=5
        )

        if response.status_code == 201:
            result = response.json()
            print(f" {GREEN}✓ Queued (job #{result['id']}){RESET}")
            return True, preview_config
        else:
            print(f" {RED}✗ Failed (status {response.status_code}){RESET}")
            return False, None

    except requests.exceptions.ConnectionError:
        print(f" {RED}✗ API server not running{RESET}")
        return False, None
    except requests.exceptions.Timeout:
        print(f" {RED}✗ Timeout{RESET}")
        return False, None
    except Exception as e:
        print(f" {RED}✗ {str(e)}{RESET}")
        return False, None


def generate_preview(lora_path, output_path, prompt=None, width=640, height=640, steps=30, guidance_scale=8.0, weight=1.0, negative_prompt=None):
    """Generate preview image for LoRA locally (synchronous)

    Args:
        prompt: Custom prompt (if None, auto-extracts from filename)

    Returns:
        tuple: (success: bool, preview_config: dict)
    """

    if not GENERATE_SCRIPT.exists():
        print(f"{RED}Generate script not found: {GENERATE_SCRIPT}{RESET}")
        return False, None

    if not VENV_PYTHON.exists():
        print(f"{RED}Python venv not found: {VENV_PYTHON}{RESET}")
        return False, None

    # Auto-extract trigger words from filename if no prompt provided
    if prompt is None:
        prompt = extract_trigger_words(lora_path.name)
        print(f"    {BLUE}Auto-detected prompt: '{prompt}'{RESET}")

    full_prompt = f"{prompt}, high quality, detailed, professional"

    cmd = [
        str(VENV_PYTHON),
        str(GENERATE_SCRIPT),
        '--prompt', full_prompt,
        '--lora-paths', str(lora_path),
        '--lora-weights', str(weight),
        '--width', str(width),
        '--height', str(height),
        '--steps', str(steps),
        '--guidance-scale', str(guidance_scale),
        '--output', str(output_path)
    ]

    # Add negative prompt if provided
    if negative_prompt:
        cmd.extend(['--negative-prompt', negative_prompt])

    # Store preview config (will be saved as global config in index)
    preview_config = {
        'prompt': prompt,
        'full_prompt': full_prompt,
        'width': width,
        'height': height,
        'steps': steps,
        'guidance_scale': guidance_scale,
        'weight': weight,
        'negative_prompt_source': 'config.yaml' if negative_prompt else None,
        'negative_prompt_length': len(negative_prompt) if negative_prompt else 0,
        'note': 'All previews use these settings for consistency'
    }

    try:
        print(f"    {BLUE}Generating preview (steps={steps}, guidance={guidance_scale})...{RESET}", end='', flush=True)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
            timeout=600  # 10 minute timeout (increased from 180)
        )

        if result.returncode == 0 and output_path.exists():
            print(f" {GREEN}✓{RESET}")
            return True, preview_config
        else:
            print(f" {RED}✗{RESET}")
            if result.stderr:
                print(f"    {RED}Error: {result.stderr[:200]}{RESET}")
            return False, None

    except subprocess.TimeoutExpired:
        print(f" {RED}✗ Timeout{RESET}")
        return False, None
    except Exception as e:
        print(f" {RED}✗ {str(e)}{RESET}")
        return False, None


def organize_lora(lora_file, lora_base_dir, index, skip_preview=False, queue_previews=False, config=None):
    """
    Organize a single LoRA file:
    1. Test compatibility
    2. Create folder
    3. Move file
    4. Generate/queue preview
    5. Create config
    6. Update index

    Args:
        skip_preview: Skip preview generation entirely
        queue_previews: Submit preview jobs to API queue instead of generating locally
        config: Main config dict (for negative_prompt, etc.)

    Returns:
        tuple: (success: bool, preview_config: dict or None)
    """

    print(f"\n{BLUE}Processing: {lora_file.name}{RESET}")
    print(f"  Size: {format_size(lora_file.stat().st_size)}")
    
    # Check compatibility
    is_compatible, reason, details = check_lora_compatibility(lora_file)

    if not is_compatible:
        print(f"  {RED}✗ Incompatible: {reason.upper()}{RESET} - {details}")

        # Move to _incompatible
        incompatible_dir = lora_base_dir / '_incompatible'
        incompatible_dir.mkdir(exist_ok=True)

        dest = incompatible_dir / f"{reason}_{lora_file.name}"
        try:
            shutil.move(str(lora_file), str(dest))
            print(f"  {YELLOW}→ Moved to: _incompatible/{dest.name}{RESET}")
            return False, None
        except Exception as e:
            print(f"  {RED}Error moving file: {e}{RESET}")
            return False, None
    
    print(f"  {GREEN}✓ Compatible: {details}{RESET}")
    
    # Create folder
    folder_name = sanitize_name(lora_file.name)
    lora_folder = lora_base_dir / folder_name
    
    if lora_folder.exists():
        # Folder exists, add numeric suffix
        counter = 1
        while (lora_base_dir / f"{folder_name}_{counter}").exists():
            counter += 1
        folder_name = f"{folder_name}_{counter}"
        lora_folder = lora_base_dir / folder_name
    
    try:
        lora_folder.mkdir()
        print(f"  {GREEN}✓ Created folder: {folder_name}/{RESET}")
    except Exception as e:
        print(f"  {RED}✗ Failed to create folder: {e}{RESET}")
        return False, None
    
    # Move LoRA file into folder
    dest_file = lora_folder / lora_file.name
    try:
        shutil.move(str(lora_file), str(dest_file))
        print(f"  {GREEN}✓ Moved file into folder{RESET}")
    except Exception as e:
        print(f"  {RED}✗ Failed to move file: {e}{RESET}")
        # Clean up folder
        shutil.rmtree(lora_folder, ignore_errors=True)
        return False, None
    
    # Generate or queue preview
    preview_filename = 'preview.png'
    preview_path = lora_folder / preview_filename

    preview_success = False
    preview_config = None
    if not skip_preview:
        # Get negative prompt from config
        negative_prompt = None
        if config and 'generation' in config:
            negative_prompt = config['generation'].get('negative_prompt')

        if queue_previews:
            # Submit preview job to API queue
            preview_success, preview_config = queue_preview_job(
                dest_file,
                preview_path,
                prompt=None,  # Auto-detect from filename
                steps=30,
                guidance_scale=8.0,
                weight=1.0,
                negative_prompt=negative_prompt
            )
        else:
            # Generate preview locally (synchronous)
            preview_success, preview_config = generate_preview(
                dest_file,
                preview_path,
                prompt=None,  # Auto-detect from filename
                steps=30,
                guidance_scale=8.0,
                weight=1.0,
                negative_prompt=negative_prompt
            )
    else:
        print(f"  {YELLOW}⊘ Skipping preview generation{RESET}")
    
    # Create config
    config_success = create_lora_config(
        lora_folder,
        dest_file,
        preview_filename if preview_success else None,
        default_weight=0.6
    )
    
    if config_success:
        print(f"  {GREEN}✓ Created config.yaml{RESET}")
    else:
        print(f"  {YELLOW}⚠ Failed to create config{RESET}")
    
    # Update index entry (preview_config will be stored globally, not per-entry)
    index_entry = {
        'filename': lora_file.name,
        'folder': folder_name,
        'compatible': True,
        'format': 'sd15',
        'has_preview': preview_success,
        'has_config': config_success,
        'organized_at': datetime.now().isoformat()
    }

    index[folder_name] = index_entry

    print(f"  {GREEN}✓ Added to index{RESET}")
    print(f"{GREEN}✓ Organization complete: {folder_name}/{RESET}")

    # Return preview config to be saved globally
    return True, preview_config if preview_success else None


def reconcile_index(lora_base_dir, index):
    """
    Reconcile index against actual folders
    - Verify all indexed folders exist
    - Verify all folders are in index
    - Report discrepancies
    """
    print(f"\n{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}Reconciling index...{RESET}")
    print(f"{BLUE}{'='*80}{RESET}\n")
    
    errors = []
    warnings = []
    
    # Get all folders (exclude special directories)
    actual_folders = {d.name for d in lora_base_dir.iterdir()
                     if d.is_dir() and not d.name.startswith('_') and not d.name.startswith('.')}

    # Get indexed folders
    indexed_folders = set(index.keys())
    
    # Check for folders in index but not on disk
    missing_folders = indexed_folders - actual_folders
    if missing_folders:
        for folder in missing_folders:
            errors.append(f"Indexed folder missing from disk: {folder}")
            print(f"{RED}✗ Missing: {folder} (in index but not on disk){RESET}")
    
    # Check for folders on disk but not in index
    unindexed_folders = actual_folders - indexed_folders
    if unindexed_folders:
        for folder in unindexed_folders:
            warnings.append(f"Folder not in index: {folder}")
            print(f"{YELLOW}⚠ Unindexed: {folder} (on disk but not in index){RESET}")
    
    # Verify folder contents
    for folder_name in actual_folders & indexed_folders:
        folder_path = lora_base_dir / folder_name
        
        # Check for config file
        config_path = folder_path / 'config.yaml'
        if not config_path.exists():
            warnings.append(f"Missing config: {folder_name}/config.yaml")
            print(f"{YELLOW}⚠ {folder_name}: Missing config.yaml{RESET}")
        
        # Check for LoRA file
        lora_files = list(folder_path.glob('*.safetensors'))
        if not lora_files:
            errors.append(f"No LoRA file in folder: {folder_name}")
            print(f"{RED}✗ {folder_name}: No .safetensors file found{RESET}")
        elif len(lora_files) > 1:
            warnings.append(f"Multiple LoRA files in folder: {folder_name}")
            print(f"{YELLOW}⚠ {folder_name}: Multiple .safetensors files{RESET}")
    
    # Summary
    print(f"\n{BLUE}Reconciliation Summary:{RESET}")
    print(f"  Indexed folders: {len(indexed_folders)}")
    print(f"  Actual folders: {len(actual_folders)}")
    print(f"  In sync: {len(actual_folders & indexed_folders)}")
    
    if errors:
        print(f"\n{RED}Errors ({len(errors)}):{RESET}")
        for error in errors:
            print(f"  {RED}✗{RESET} {error}")
    
    if warnings:
        print(f"\n{YELLOW}Warnings ({len(warnings)}):{RESET}")
        for warning in warnings:
            print(f"  {YELLOW}⚠{RESET} {warning}")
    
    if not errors and not warnings:
        print(f"\n{GREEN}✓ Index is in sync with folders{RESET}")
    
    return len(errors) == 0


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Organize new LoRA files and maintain index',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Organize new LoRAs found in root
  python scripts/organize_loras.py

  # Skip preview generation (faster)
  python scripts/organize_loras.py --no-preview

  # Reconcile only (no new organization)
  python scripts/organize_loras.py --reconcile-only
        """
    )
    
    parser.add_argument(
        '--lora-dir',
        default='/mnt/speedy/imagineer/models/lora',
        help='Base LoRA directory (default: /mnt/speedy/imagineer/models/lora)'
    )
    
    parser.add_argument(
        '--no-preview',
        action='store_true',
        help='Skip preview image generation'
    )

    parser.add_argument(
        '--queue-previews',
        action='store_true',
        help='Queue preview jobs via API server instead of generating locally'
    )

    parser.add_argument(
        '--reconcile-only',
        action='store_true',
        help='Only reconcile index, don\'t organize new files'
    )
    
    args = parser.parse_args()
    
    lora_base_dir = Path(args.lora_dir)
    
    if not lora_base_dir.exists():
        print(f"{RED}Error: LoRA directory not found: {lora_base_dir}{RESET}")
        return 1
    
    # Load index
    index = load_index(lora_base_dir)
    print(f"{BLUE}Loaded index: {len(index)} entries{RESET}")

    # Load main config for negative prompt, etc.
    config = load_config()
    if config:
        print(f"{BLUE}Loaded config: {CONFIG_PATH}{RESET}")
    else:
        print(f"{YELLOW}Warning: Could not load config.yaml, using defaults{RESET}")

    if not args.reconcile_only:
        # Find new LoRAs in root (not in subdirectories, not in index)
        new_loras = []
        
        for lora_file in lora_base_dir.glob('*.safetensors'):
            # Check if it's a direct child (not in subfolder)
            if lora_file.parent == lora_base_dir:
                # Check if already in index
                if not any(entry.get('filename') == lora_file.name for entry in index.values()):
                    new_loras.append(lora_file)
        
        if new_loras:
            print(f"\n{BLUE}{'='*80}{RESET}")
            print(f"{BLUE}Found {len(new_loras)} new LoRA(s) to organize{RESET}")
            print(f"{BLUE}{'='*80}{RESET}")
            
            organized_count = 0
            last_preview_config = None

            for lora_file in sorted(new_loras):
                success, preview_config = organize_lora(
                    lora_file,
                    lora_base_dir,
                    index,
                    skip_preview=args.no_preview,
                    queue_previews=args.queue_previews,
                    config=config
                )
                if success:
                    organized_count += 1
                    # Store preview config from successful preview generation
                    if preview_config:
                        last_preview_config = preview_config

            # Save updated index and preview config
            if organized_count > 0:
                if save_index(lora_base_dir, index):
                    print(f"\n{GREEN}✓ Index updated ({organized_count} new entries){RESET}")
                else:
                    print(f"\n{RED}✗ Failed to save index{RESET}")

                # Save preview config if we generated any previews
                if last_preview_config:
                    if save_preview_config(lora_base_dir, last_preview_config):
                        print(f"{GREEN}✓ Preview config updated{RESET}")
                    else:
                        print(f"{YELLOW}⚠ Failed to save preview config{RESET}")
        else:
            print(f"\n{YELLOW}No new LoRAs found in root directory{RESET}")
    
    # Reconcile
    if not reconcile_index(lora_base_dir, index):
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
