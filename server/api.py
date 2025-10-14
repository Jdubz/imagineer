"""
Imagineer API Server
Flask-based REST API for managing image generation
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import yaml
import json
import os
import sys
import csv
from pathlib import Path
from datetime import datetime
import subprocess
import threading
import queue

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

app = Flask(__name__, static_folder='../public', static_url_path='')
CORS(app)

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_PATH = PROJECT_ROOT / 'config.yaml'
VENV_PYTHON = PROJECT_ROOT / 'venv' / 'bin' / 'python'
GENERATE_SCRIPT = PROJECT_ROOT / 'examples' / 'generate.py'

# Load sets directory from config (will be set after config loads)
SETS_DIR = None
SETS_CONFIG_PATH = None

# Job queue
job_queue = queue.Queue()
job_history = []
current_job = None


def load_config():
    """Load config.yaml and initialize sets paths"""
    global SETS_DIR, SETS_CONFIG_PATH

    with open(CONFIG_PATH, 'r') as f:
        config = yaml.safe_load(f)

    # Initialize sets directory paths from config
    if 'sets' in config and 'directory' in config['sets']:
        SETS_DIR = Path(config['sets']['directory'])
        SETS_CONFIG_PATH = SETS_DIR / 'config.yaml'
    else:
        # Fallback to repo location if not in config
        SETS_DIR = PROJECT_ROOT / 'data' / 'sets'
        SETS_CONFIG_PATH = SETS_DIR / 'config.yaml'

    return config


def save_config(config):
    """Save config.yaml"""
    with open(CONFIG_PATH, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)


def load_sets_config():
    """Load sets configuration, dynamically discovering sets from CSV files

    Returns:
        Dict with set configurations. Merges config.yaml with auto-discovered CSV files.
    """
    # Start with empty config
    config = {}

    # Load config.yaml if it exists
    if SETS_CONFIG_PATH and SETS_CONFIG_PATH.exists():
        with open(SETS_CONFIG_PATH, 'r') as f:
            config = yaml.safe_load(f) or {}

    # Dynamically discover CSV files in sets directory
    if SETS_DIR and SETS_DIR.exists():
        for csv_file in SETS_DIR.glob('*.csv'):
            set_id = csv_file.stem

            # If not in config, create default config
            if set_id not in config:
                # Create friendly name from file name
                name = set_id.replace('_', ' ').title()

                config[set_id] = {
                    'name': name,
                    'description': f'Auto-discovered set: {name}',
                    'csv_path': str(csv_file),
                    'base_prompt': f'A {name.lower()} card',
                    'prompt_template': '{name}, {description}' if set_id != 'card_deck' else '{value} of {suit}, {personality}',
                    'style_suffix': 'card design, professional illustration',
                    'example_theme': 'artistic style with creative lighting'
                }
            else:
                # Ensure csv_path is set correctly from SETS_DIR
                if 'csv_path' not in config[set_id] or not config[set_id]['csv_path'].startswith(str(SETS_DIR)):
                    config[set_id]['csv_path'] = str(SETS_DIR / f"{set_id}.csv")

    return config


def get_set_config(set_name):
    """Get configuration for a specific set

    Args:
        set_name: Name of the set

    Returns:
        Dict with set configuration or None if not found
    """
    sets_config = load_sets_config()
    return sets_config.get(set_name)


def discover_set_loras(set_name, config):
    """Dynamically discover LoRAs from set-specific folder

    Looks for LoRAs in /mnt/speedy/imagineer/models/lora/{set_name}/
    and returns list of LoRA configurations with paths and weights.

    Args:
        set_name: Name of the set
        config: Main config dict containing model paths

    Returns:
        List of dicts with 'path' and 'weight' keys, or empty list if no LoRAs found
    """
    # Get lora base directory from config
    lora_base_dir = Path(config['model'].get('cache_dir', '/mnt/speedy/imagineer/models')) / 'lora'
    set_lora_dir = lora_base_dir / set_name

    if not set_lora_dir.exists() or not set_lora_dir.is_dir():
        return []

    # Find all .safetensors files in the set folder
    lora_files = sorted(set_lora_dir.glob('*.safetensors'))

    if not lora_files:
        return []

    # Build list of LoRA configs with default weights
    # Default weight distributed evenly, but not exceeding 1.0 total
    num_loras = len(lora_files)
    default_weight = min(0.8 / num_loras, 0.6)  # Cap individual weights at 0.6

    loras = []
    for lora_file in lora_files:
        loras.append({
            'path': str(lora_file),
            'weight': default_weight
        })

    return loras


def construct_prompt(base_prompt, user_theme, csv_data, prompt_template, style_suffix):
    """Construct the final prompt from components

    Order: [Base] [User Theme] [CSV Data via Template] [Style Suffix]
    This order follows Stable Diffusion best practices where front words have strongest influence.

    Args:
        base_prompt: Base description (e.g., "A single playing card")
        user_theme: User's art style theme (e.g., "barnyard animals under a full moon")
        csv_data: Dict of CSV row data
        prompt_template: Template string with {column} placeholders
        style_suffix: Technical/style refinement terms

    Returns:
        Complete prompt string
    """
    # Replace placeholders in template with CSV data
    csv_text = prompt_template
    for key, value in csv_data.items():
        csv_text = csv_text.replace(f'{{{key}}}', value)

    # Construct final prompt with optimal ordering
    parts = []
    if base_prompt:
        parts.append(base_prompt)
    if user_theme:
        parts.append(f"Art style: {user_theme}")
    if csv_text:
        parts.append(csv_text)
    if style_suffix:
        parts.append(style_suffix)

    return ". ".join(parts)


def load_set_data(set_name):
    """Load data from a CSV set file

    Args:
        set_name: Name of the set (without .csv extension)

    Returns:
        List of dicts with all CSV columns as keys

    Raises:
        FileNotFoundError: If set doesn't exist
        ValueError: If CSV is malformed
    """
    # Security: Validate set_name to prevent path traversal
    if '..' in set_name or '/' in set_name or '\\' in set_name:
        raise ValueError('Invalid set name')

    # Get set config to find CSV path
    set_config = get_set_config(set_name)
    if set_config and 'csv_path' in set_config:
        set_path = Path(set_config['csv_path'])
    else:
        # Fallback to SETS_DIR if config doesn't specify path
        if not SETS_DIR:
            raise FileNotFoundError('Sets directory not configured')
        set_path = SETS_DIR / f"{set_name}.csv"

    if not set_path.exists():
        raise FileNotFoundError(f'Set "{set_name}" not found at {set_path}')

    items = []
    with open(set_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        if not reader.fieldnames:
            raise ValueError('CSV must have column headers')

        for row in reader:
            # Strip whitespace from all values
            item = {key: value.strip() for key, value in row.items()}
            items.append(item)

    if not items:
        raise ValueError('Set is empty')

    return items


def list_available_sets():
    """List all available CSV sets from configuration

    Returns:
        List of set IDs
    """
    sets_config = load_sets_config()
    return sorted(sets_config.keys())


def generate_random_theme():
    """Generate a random art style theme for inspiration

    Returns:
        A random theme string
    """
    import random

    # Art styles
    styles = [
        "watercolor", "oil painting", "digital art", "pencil sketch", "ink drawing",
        "pastel", "acrylic", "charcoal", "mixed media", "gouache", "airbrush",
        "impressionist", "art nouveau", "art deco", "baroque", "renaissance",
        "surrealist", "abstract", "minimalist", "pop art", "cyberpunk", "steampunk",
        "vaporwave", "synthwave", "retro", "vintage", "modern", "contemporary"
    ]

    # Settings/environments
    environments = [
        "mystical forest", "cosmic nebula", "underwater world", "desert landscape",
        "mountain peaks", "ancient ruins", "futuristic city", "enchanted garden",
        "stormy ocean", "peaceful meadow", "dark cavern", "floating islands",
        "crystal palace", "volcanic terrain", "frozen tundra", "tropical paradise",
        "haunted mansion", "steampunk workshop", "neon-lit streets", "starlit sky"
    ]

    # Lighting/mood
    moods = [
        "ethereal glowing light", "dramatic shadows", "soft diffused lighting",
        "golden hour glow", "moonlit atmosphere", "harsh sunlight", "bioluminescent glow",
        "candlelit ambiance", "aurora borealis", "sunset colors", "dawn light",
        "neon glow", "firelight", "lightning flashes", "rainbow light", "foggy mist"
    ]

    # Color palettes
    colors = [
        "deep purples and blues", "warm oranges and reds", "cool greens and teals",
        "monochromatic grayscale", "vibrant rainbow", "pastel pinks and lavenders",
        "earth tones", "metallic gold and silver", "black and gold", "navy and cream",
        "emerald and sapphire", "crimson and gold", "turquoise and coral"
    ]

    # Construct random theme
    style = random.choice(styles)
    environment = random.choice(environments)
    mood = random.choice(moods)
    color = random.choice(colors)

    # Randomly choose 2-3 components
    components = random.sample([
        f"{style} style",
        environment,
        mood,
        color
    ], k=random.randint(2, 3))

    return ", ".join(components)


def process_jobs():
    """Background worker to process generation jobs"""
    global current_job

    while True:
        job = job_queue.get()
        if job is None:
            break

        current_job = job
        job['status'] = 'running'
        job['started_at'] = datetime.now().isoformat()

        try:
            # Build command
            cmd = [
                str(VENV_PYTHON),
                str(GENERATE_SCRIPT),
                '--prompt', job['prompt']
            ]

            # Add optional parameters
            if job.get('seed'):
                cmd.extend(['--seed', str(job['seed'])])
            if job.get('steps'):
                cmd.extend(['--steps', str(job['steps'])])
            if job.get('width'):
                cmd.extend(['--width', str(job['width'])])
            if job.get('height'):
                cmd.extend(['--height', str(job['height'])])
            if job.get('guidance_scale'):
                cmd.extend(['--guidance-scale', str(job['guidance_scale'])])
            if job.get('negative_prompt'):
                cmd.extend(['--negative-prompt', job['negative_prompt']])
            # Handle LoRAs (backward compatible with single LoRA)
            if job.get('lora_paths') and job.get('lora_weights'):
                # Multi-LoRA format
                cmd.extend(['--lora-paths'] + job['lora_paths'])
                cmd.extend(['--lora-weights'] + [str(w) for w in job['lora_weights']])
            elif job.get('lora_path'):
                # Single LoRA format (backward compatibility)
                cmd.extend(['--lora-path', job['lora_path']])
                if job.get('lora_weight'):
                    cmd.extend(['--lora-weight', str(job['lora_weight'])])

            # Handle output path
            if job.get('output'):
                # Direct output path specified (e.g., for preview generation)
                cmd.extend(['--output', job['output']])
            elif job.get('output_dir') and job.get('batch_item_name'):
                # For batch jobs, specify output directory
                safe_name = "".join(c for c in job['batch_item_name'] if c.isalnum() or c in (' ', '_', '-')).strip()
                safe_name = safe_name.replace(' ', '_')
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_path = Path(job['output_dir']) / f"{timestamp}_{safe_name}.png"
                cmd.extend(['--output', str(output_path)])

            # Run generation
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=PROJECT_ROOT
            )

            if result.returncode == 0:
                job['status'] = 'completed'
                job['output'] = result.stdout
                # Extract output path from stdout
                for line in result.stdout.split('\n'):
                    if 'Image saved to:' in line:
                        job['output_path'] = line.split('Image saved to:')[1].strip()
            else:
                job['status'] = 'failed'
                job['error'] = result.stderr

        except Exception as e:
            job['status'] = 'failed'
            job['error'] = str(e)

        job['completed_at'] = datetime.now().isoformat()
        job_history.append(job)
        current_job = None
        job_queue.task_done()


# Start background worker
worker_thread = threading.Thread(target=process_jobs, daemon=True)
worker_thread.start()


@app.route('/')
def index():
    """Serve the web UI"""
    return send_from_directory('../public', 'index.html')


@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration"""
    config = load_config()
    return jsonify(config)


@app.route('/api/config', methods=['PUT'])
def update_config():
    """Update configuration - DANGEROUS: Allows full config replacement"""
    try:
        new_config = request.json

        if not new_config or not isinstance(new_config, dict):
            return jsonify({'success': False, 'error': 'Invalid configuration'}), 400

        # Security: Validate required keys exist
        required_keys = ['model', 'generation', 'output']
        for key in required_keys:
            if key not in new_config:
                return jsonify({'success': False, 'error': f'Missing required key: {key}'}), 400

        # Validate paths don't escape project directory
        if 'output' in new_config and 'directory' in new_config['output']:
            output_path = Path(new_config['output']['directory'])
            # Only allow absolute paths or paths within reasonable locations
            if '..' in str(output_path):
                return jsonify({'success': False, 'error': 'Invalid output directory path'}), 400

        save_config(new_config)
        return jsonify({'success': True, 'message': 'Configuration updated'})
    except Exception as e:
        return jsonify({'success': False, 'error': 'Failed to update configuration'}), 400


@app.route('/api/config/generation', methods=['PUT'])
def update_generation_config():
    """Update just the generation settings"""
    try:
        updates = request.json

        if not updates or not isinstance(updates, dict):
            return jsonify({'success': False, 'error': 'Invalid data'}), 400

        # Security: Only allow specific generation parameters
        allowed_keys = ['width', 'height', 'steps', 'guidance_scale', 'negative_prompt', 'batch_size', 'num_images']
        for key in updates.keys():
            if key not in allowed_keys:
                return jsonify({'success': False, 'error': f'Invalid parameter: {key}'}), 400

        config = load_config()
        config['generation'].update(updates)
        save_config(config)
        return jsonify({'success': True, 'config': config['generation']})
    except Exception as e:
        return jsonify({'success': False, 'error': 'Failed to update generation config'}), 400


@app.route('/api/generate', methods=['POST'])
def generate():
    """Submit a new image generation job"""
    try:
        data = request.json

        if not data or not data.get('prompt'):
            return jsonify({'success': False, 'error': 'Prompt is required'}), 400

        # Validate prompt length
        prompt = str(data['prompt']).strip()
        if not prompt:
            return jsonify({'success': False, 'error': 'Prompt is required'}), 400
        if len(prompt) > 2000:
            return jsonify({'success': False, 'error': 'Prompt too long (max 2000 chars)'}), 400

        # Validate and sanitize integer parameters
        seed = data.get('seed')
        if seed is not None:
            try:
                seed = int(seed)
                if seed < 0 or seed > 2147483647:
                    return jsonify({'success': False, 'error': 'Seed must be between 0 and 2147483647'}), 400
            except (ValueError, TypeError):
                return jsonify({'success': False, 'error': 'Invalid seed value'}), 400

        steps = data.get('steps')
        if steps is not None:
            try:
                steps = int(steps)
                if steps < 1 or steps > 150:
                    return jsonify({'success': False, 'error': 'Steps must be between 1 and 150'}), 400
            except (ValueError, TypeError):
                return jsonify({'success': False, 'error': 'Invalid steps value'}), 400

        width = data.get('width')
        if width is not None:
            try:
                width = int(width)
                if width < 64 or width > 2048 or width % 8 != 0:
                    return jsonify({'success': False, 'error': 'Width must be between 64-2048 and divisible by 8'}), 400
            except (ValueError, TypeError):
                return jsonify({'success': False, 'error': 'Invalid width value'}), 400

        height = data.get('height')
        if height is not None:
            try:
                height = int(height)
                if height < 64 or height > 2048 or height % 8 != 0:
                    return jsonify({'success': False, 'error': 'Height must be between 64-2048 and divisible by 8'}), 400
            except (ValueError, TypeError):
                return jsonify({'success': False, 'error': 'Invalid height value'}), 400

        guidance_scale = data.get('guidance_scale')
        if guidance_scale is not None:
            try:
                guidance_scale = float(guidance_scale)
                if guidance_scale < 0 or guidance_scale > 30:
                    return jsonify({'success': False, 'error': 'Guidance scale must be between 0 and 30'}), 400
            except (ValueError, TypeError):
                return jsonify({'success': False, 'error': 'Invalid guidance scale value'}), 400

        negative_prompt = data.get('negative_prompt')
        if negative_prompt is not None:
            negative_prompt = str(negative_prompt).strip()
            if len(negative_prompt) > 2000:
                return jsonify({'success': False, 'error': 'Negative prompt too long (max 2000 chars)'}), 400

        # Handle output path
        output = data.get('output')
        if output is not None:
            output = str(output).strip()
            # Security: Validate output path doesn't escape allowed directories
            if '..' in output or output.startswith('/'):
                if not Path(output).is_absolute():
                    return jsonify({'success': False, 'error': 'Invalid output path'}), 400

        # Handle LoRA paths and weights
        lora_paths = data.get('lora_paths')
        lora_weights = data.get('lora_weights')

        job = {
            'id': len(job_history) + job_queue.qsize() + 1,
            'prompt': prompt,
            'seed': seed,
            'steps': steps,
            'width': width,
            'height': height,
            'guidance_scale': guidance_scale,
            'negative_prompt': negative_prompt,
            'output': output,
            'lora_paths': lora_paths,
            'lora_weights': lora_weights,
            'status': 'queued',
            'submitted_at': datetime.now().isoformat()
        }

        job_queue.put(job)

        # Return 201 Created with Location header pointing to job status
        response = jsonify({
            'id': job['id'],
            'status': job['status'],
            'submitted_at': job['submitted_at'],
            'queue_position': job_queue.qsize(),
            'prompt': job['prompt']
        })
        response.status_code = 201
        response.headers['Location'] = f"/api/jobs/{job['id']}"

        return response

    except Exception as e:
        return jsonify({'error': 'Invalid request'}), 400


@app.route('/api/sets', methods=['GET'])
def get_sets():
    """List available CSV sets with their configuration"""
    try:
        sets_config = load_sets_config()
        sets_list = []

        for set_name, config in sets_config.items():
            sets_list.append({
                'id': set_name,
                'name': config.get('name', set_name),
                'description': config.get('description', ''),
                'example_theme': config.get('example_theme', '')
            })

        return jsonify({'sets': sets_list})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/sets/<set_name>/info', methods=['GET'])
def get_set_info(set_name):
    """Get detailed information about a specific set"""
    try:
        set_config = get_set_config(set_name)
        if not set_config:
            return jsonify({'error': f'Set "{set_name}" not found'}), 404

        # Load CSV to get item count
        try:
            set_items = load_set_data(set_name)
            item_count = len(set_items)
        except:
            item_count = 0

        return jsonify({
            'id': set_name,
            'name': set_config.get('name', set_name),
            'description': set_config.get('description', ''),
            'example_theme': set_config.get('example_theme', ''),
            'item_count': item_count,
            'base_prompt': set_config.get('base_prompt', ''),
            'style_suffix': set_config.get('style_suffix', '')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/themes/random', methods=['GET'])
def get_random_theme():
    """Generate a random art style theme for inspiration"""
    try:
        theme = generate_random_theme()
        return jsonify({'theme': theme})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/generate/batch', methods=['POST'])
def generate_batch():
    """Submit batch generation from CSV set

    Creates multiple jobs by combining user theme with set configuration.
    All images will be saved in a subfolder named after the batch.
    """
    try:
        data = request.json

        if not data or not data.get('set_name'):
            return jsonify({'error': 'set_name is required'}), 400

        if not data.get('user_theme'):
            return jsonify({'error': 'user_theme is required'}), 400

        set_name = str(data['set_name']).strip()
        user_theme = str(data['user_theme']).strip()

        if not user_theme:
            return jsonify({'error': 'user_theme cannot be empty'}), 400

        if len(user_theme) > 500:
            return jsonify({'error': 'user_theme too long (max 500 chars)'}), 400

        # Load set configuration
        set_config = get_set_config(set_name)
        if not set_config:
            return jsonify({'error': f'Set "{set_name}" not found in configuration'}), 404

        # Load set data
        try:
            set_items = load_set_data(set_name)
        except FileNotFoundError:
            return jsonify({'error': f'Set "{set_name}" CSV file not found'}), 404
        except ValueError as e:
            return jsonify({'error': str(e)}), 400

        # Get optional parameters (applied to all jobs in batch)
        seed = data.get('seed')
        if seed is not None:
            try:
                seed = int(seed)
                if seed < 0 or seed > 2147483647:
                    return jsonify({'error': 'Seed must be between 0 and 2147483647'}), 400
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid seed value'}), 400

        steps = data.get('steps')
        if steps is not None:
            try:
                steps = int(steps)
                if steps < 1 or steps > 150:
                    return jsonify({'error': 'Steps must be between 1 and 150'}), 400
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid steps value'}), 400

        width = data.get('width')
        if width is not None:
            try:
                width = int(width)
                if width < 64 or width > 2048 or width % 8 != 0:
                    return jsonify({'error': 'Width must be between 64-2048 and divisible by 8'}), 400
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid width value'}), 400

        height = data.get('height')
        if height is not None:
            try:
                height = int(height)
                if height < 64 or height > 2048 or height % 8 != 0:
                    return jsonify({'error': 'Height must be between 64-2048 and divisible by 8'}), 400
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid height value'}), 400

        guidance_scale = data.get('guidance_scale')
        if guidance_scale is not None:
            try:
                guidance_scale = float(guidance_scale)
                if guidance_scale < 0 or guidance_scale > 30:
                    return jsonify({'error': 'Guidance scale must be between 0 and 30'}), 400
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid guidance scale value'}), 400

        negative_prompt = data.get('negative_prompt')
        if negative_prompt is not None:
            negative_prompt = str(negative_prompt).strip()
            if len(negative_prompt) > 2000:
                return jsonify({'error': 'Negative prompt too long (max 2000 chars)'}), 400

        # Create batch ID and output subfolder
        batch_id = f"{set_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        config = load_config()
        batch_output_dir = Path(config['output']['directory']) / batch_id

        # Create the subfolder
        batch_output_dir.mkdir(parents=True, exist_ok=True)

        # Extract set configuration
        base_prompt = set_config.get('base_prompt', '')
        prompt_template = set_config.get('prompt_template', '')
        style_suffix = set_config.get('style_suffix', '')

        # Use set-specific dimensions if not provided by user
        if width is None and 'width' in set_config:
            width = set_config['width']
        if height is None and 'height' in set_config:
            height = set_config['height']

        # Use set-specific negative prompt if not provided by user
        # If user provided one, append set's negative prompt to it
        set_negative_prompt = set_config.get('negative_prompt', '')
        if negative_prompt and set_negative_prompt:
            negative_prompt = f"{negative_prompt}, {set_negative_prompt}"
        elif set_negative_prompt:
            negative_prompt = set_negative_prompt

        # Create jobs for each item in the set
        job_ids = []
        for item in set_items:
            # Construct prompt using optimal ordering
            prompt = construct_prompt(
                base_prompt=base_prompt,
                user_theme=user_theme,
                csv_data=item,
                prompt_template=prompt_template,
                style_suffix=style_suffix
            )

            # Create a name for the file from available columns
            # Priority: value+suit, name, first column
            if 'value' in item and 'suit' in item:
                item_name = f"{item['value']}_of_{item['suit']}"
            elif 'name' in item:
                item_name = item['name']
            else:
                # Use first column value
                item_name = next(iter(item.values()))

            job_id = len(job_history) + job_queue.qsize() + 1

            job = {
                'id': job_id,
                'prompt': prompt,
                'seed': seed,
                'steps': steps,
                'width': width,
                'height': height,
                'guidance_scale': guidance_scale,
                'negative_prompt': negative_prompt,
                'status': 'queued',
                'submitted_at': datetime.now().isoformat(),
                'batch_id': batch_id,
                'batch_item_name': item_name,
                'batch_item_data': item,  # Store full item data for reference
                'output_dir': str(batch_output_dir)  # Custom output directory for this job
            }

            # Add LoRA parameters - try multiple sources in priority order:
            # 1. Explicit 'loras' config in set config (multi-LoRA)
            # 2. Dynamic discovery from set-specific folder
            # 3. Old 'lora' config in set config (single LoRA, backward compatibility)
            loras_to_load = None

            if 'loras' in set_config and set_config['loras']:
                # Explicit multi-LoRA format in config
                loras = set_config['loras']
                if isinstance(loras, list) and len(loras) > 0:
                    loras_to_load = loras
            else:
                # Try dynamic discovery from set folder
                discovered_loras = discover_set_loras(set_name, config)
                if discovered_loras:
                    loras_to_load = discovered_loras
                    # Apply weight overrides from config if specified
                    if 'lora_weights' in set_config:
                        weight_overrides = set_config['lora_weights']
                        if isinstance(weight_overrides, dict):
                            # Dict format: {filename: weight}
                            for lora in loras_to_load:
                                lora_filename = Path(lora['path']).name
                                if lora_filename in weight_overrides:
                                    lora['weight'] = weight_overrides[lora_filename]
                        elif isinstance(weight_overrides, list):
                            # List format: apply weights in order
                            for i, weight in enumerate(weight_overrides):
                                if i < len(loras_to_load):
                                    loras_to_load[i]['weight'] = weight

            if loras_to_load:
                # Multi-LoRA format
                job['lora_paths'] = [lora['path'] for lora in loras_to_load if 'path' in lora]
                job['lora_weights'] = [lora.get('weight', 0.5) for lora in loras_to_load if 'path' in lora]
            elif 'lora' in set_config and set_config['lora']:
                # Old single LoRA format (backward compatibility)
                lora_config = set_config['lora']
                if 'path' in lora_config:
                    job['lora_path'] = lora_config['path']
                    job['lora_weight'] = lora_config.get('weight', 0.5)

            job_queue.put(job)
            job_ids.append(job_id)

        # Return 201 Created with batch info
        response = jsonify({
            'batch_id': batch_id,
            'set_name': set_name,
            'total_jobs': len(job_ids),
            'job_ids': job_ids,
            'output_directory': str(batch_output_dir),
            'submitted_at': datetime.now().isoformat()
        })
        response.status_code = 201
        response.headers['Location'] = f"/api/batches/{batch_id}"

        return response

    except Exception as e:
        return jsonify({'error': 'Invalid request'}), 400


@app.route('/api/jobs', methods=['GET'])
def get_jobs():
    """Get job history and current queue"""
    queue_list = list(job_queue.queue)

    return jsonify({
        'current': current_job,
        'queued': queue_list,
        'history': job_history[-50:]  # Last 50 jobs
    })


@app.route('/api/jobs/<int:job_id>', methods=['GET'])
def get_job(job_id):
    """Get specific job details"""
    # Check current job
    if current_job and current_job['id'] == job_id:
        job_response = {
            **current_job,
            'queue_position': 0,  # Currently running
            'estimated_time_remaining': None  # Could calculate based on steps
        }
        return jsonify(job_response)

    # Check queue
    position = 1
    for job in list(job_queue.queue):
        if job['id'] == job_id:
            job_response = {
                **job,
                'queue_position': position,
                'estimated_time_remaining': None  # Could estimate based on position
            }
            return jsonify(job_response)
        position += 1

    # Check history
    for job in job_history:
        if job['id'] == job_id:
            # Add duration if completed
            if job.get('started_at') and job.get('completed_at'):
                start = datetime.fromisoformat(job['started_at'])
                end = datetime.fromisoformat(job['completed_at'])
                job['duration_seconds'] = (end - start).total_seconds()
            return jsonify(job)

    return jsonify({'error': 'Job not found'}), 404


@app.route('/api/jobs/<int:job_id>', methods=['DELETE'])
def cancel_job(job_id):
    """Cancel a queued job"""
    global job_queue

    # Cannot cancel currently running job
    if current_job and current_job['id'] == job_id:
        return jsonify({'error': 'Cannot cancel job that is currently running'}), 409

    # Cannot cancel completed job
    for job in job_history:
        if job['id'] == job_id:
            return jsonify({'error': 'Cannot cancel completed job'}), 410

    # Try to remove from queue
    queue_list = list(job_queue.queue)
    found = False
    for job in queue_list:
        if job['id'] == job_id:
            job['status'] = 'cancelled'
            job['cancelled_at'] = datetime.now().isoformat()
            job_history.append(job)
            found = True
            break

    if found:
        # Rebuild queue without cancelled job
        new_queue = queue.Queue()
        for job in queue_list:
            if job['id'] != job_id:
                new_queue.put(job)

        # Replace the queue
        job_queue = new_queue

        return jsonify({'message': 'Job cancelled successfully'}), 200

    return jsonify({'error': 'Job not found'}), 404


@app.route('/api/batches', methods=['GET'])
def list_batches():
    """List all batch output directories"""
    try:
        config = load_config()
        output_dir = Path(config['output']['directory'])

        batches = []
        if output_dir.exists():
            # Find all subdirectories (batches)
            for batch_dir in sorted(output_dir.iterdir(), key=os.path.getmtime, reverse=True):
                if batch_dir.is_dir():
                    # Count images in batch
                    image_count = len(list(batch_dir.glob('*.png')))

                    batches.append({
                        'batch_id': batch_dir.name,
                        'path': str(batch_dir),
                        'image_count': image_count,
                        'created': datetime.fromtimestamp(batch_dir.stat().st_mtime).isoformat()
                    })

        return jsonify({'batches': batches})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/batches/<batch_id>', methods=['GET'])
def get_batch(batch_id):
    """Get images from a specific batch"""
    try:
        # Security: Validate batch_id to prevent path traversal
        if '..' in batch_id or '/' in batch_id or '\\' in batch_id:
            return jsonify({'error': 'Invalid batch ID'}), 400

        config = load_config()
        batch_dir = Path(config['output']['directory']) / batch_id

        if not batch_dir.exists() or not batch_dir.is_dir():
            return jsonify({'error': 'Batch not found'}), 404

        images = []
        for img_file in sorted(batch_dir.glob('*.png'), key=os.path.getmtime):
            metadata_file = img_file.with_suffix('.json')
            metadata = {}

            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)

            images.append({
                'filename': img_file.name,
                'path': str(img_file),
                'relative_path': f"{batch_id}/{img_file.name}",
                'size': img_file.stat().st_size,
                'created': datetime.fromtimestamp(img_file.stat().st_mtime).isoformat(),
                'metadata': metadata
            })

        return jsonify({
            'batch_id': batch_id,
            'image_count': len(images),
            'images': images
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/outputs', methods=['GET'])
def list_outputs():
    """List generated images (non-batch only)"""
    try:
        config = load_config()
        output_dir = Path(config['output']['directory'])

        images = []
        if output_dir.exists():
            # Only get PNG files directly in output dir (not in subdirectories)
            for img_file in sorted(output_dir.glob('*.png'), key=os.path.getmtime, reverse=True):
                metadata_file = img_file.with_suffix('.json')
                metadata = {}

                if metadata_file.exists():
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)

                images.append({
                    'filename': img_file.name,
                    'path': str(img_file),
                    'size': img_file.stat().st_size,
                    'created': datetime.fromtimestamp(img_file.stat().st_mtime).isoformat(),
                    'metadata': metadata
                })

        return jsonify({'images': images[:100]})  # Last 100 images

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/outputs/<path:filename>')
def serve_output(filename):
    """Serve a generated image"""
    try:
        config = load_config()
        output_dir = Path(config['output']['directory']).resolve()

        # Security: Validate filename to prevent path traversal
        # Check for path traversal attempts
        if '..' in filename or filename.startswith('/') or filename.startswith('\\'):
            return jsonify({'error': 'Access denied'}), 403

        # Construct the full path and resolve it
        requested_path = (output_dir / filename).resolve()

        # Security check: Ensure the resolved path is within output_dir
        if not str(requested_path).startswith(str(output_dir)):
            return jsonify({'error': 'Access denied'}), 403

        # Check if file exists and is a file (not a directory)
        if not requested_path.exists() or not requested_path.is_file():
            return jsonify({'error': 'File not found'}), 404

        # Serve the file from its directory
        return send_from_directory(requested_path.parent, requested_path.name)

    except Exception as e:
        return jsonify({'error': 'Invalid request'}), 400


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'queue_size': job_queue.qsize(),
        'current_job': current_job is not None,
        'total_completed': len(job_history)
    })


@app.route('/api/loras', methods=['GET'])
def list_loras():
    """List all organized LoRAs from index"""
    try:
        config = load_config()
        lora_base_dir = Path(config['model'].get('cache_dir', '/mnt/speedy/imagineer/models')) / 'lora'
        index_path = lora_base_dir / 'index.json'

        if not index_path.exists():
            return jsonify({'loras': []})

        with open(index_path, 'r') as f:
            index = json.load(f)

        loras = []
        for folder_name, entry in index.items():
            lora_folder = lora_base_dir / folder_name
            preview_path = lora_folder / 'preview.png'

            # Check for actual preview file existence instead of trusting the index
            has_preview = preview_path.exists()

            loras.append({
                'folder': folder_name,
                'filename': entry.get('filename'),
                'format': entry.get('format', 'sd15'),
                'compatible': entry.get('compatible', True),
                'has_preview': has_preview,  # Use actual file existence
                'has_config': entry.get('has_config', False),
                'organized_at': entry.get('organized_at'),
                'default_weight': entry.get('default_weight')
            })

        # Sort by most recently organized
        loras.sort(key=lambda x: x.get('organized_at', ''), reverse=True)

        return jsonify({'loras': loras})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/loras/<folder>/preview', methods=['GET'])
def serve_lora_preview(folder):
    """Serve LoRA preview image"""
    try:
        # Security: Validate folder name to prevent path traversal
        if '..' in folder or '/' in folder or '\\' in folder:
            return jsonify({'error': 'Invalid folder name'}), 400

        config = load_config()
        lora_base_dir = Path(config['model'].get('cache_dir', '/mnt/speedy/imagineer/models')) / 'lora'
        preview_path = lora_base_dir / folder / 'preview.png'

        if not preview_path.exists():
            return jsonify({'error': 'Preview not found'}), 404

        return send_from_directory(preview_path.parent, preview_path.name)

    except Exception as e:
        return jsonify({'error': 'Invalid request'}), 400


@app.route('/api/loras/<folder>', methods=['GET'])
def get_lora_details(folder):
    """Get detailed information about a specific LoRA"""
    try:
        # Security: Validate folder name
        if '..' in folder or '/' in folder or '\\' in folder:
            return jsonify({'error': 'Invalid folder name'}), 400

        config = load_config()
        lora_base_dir = Path(config['model'].get('cache_dir', '/mnt/speedy/imagineer/models')) / 'lora'
        lora_folder = lora_base_dir / folder
        config_path = lora_folder / 'config.yaml'

        if not lora_folder.exists():
            return jsonify({'error': 'LoRA not found'}), 404

        details = {}

        # Load config if it exists
        if config_path.exists():
            with open(config_path, 'r') as f:
                details = yaml.safe_load(f) or {}

        # Add index info
        index_path = lora_base_dir / 'index.json'
        if index_path.exists():
            with open(index_path, 'r') as f:
                index = json.load(f)
                if folder in index:
                    details.update(index[folder])

        return jsonify(details)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/sets/<set_name>/loras', methods=['GET'])
def get_set_loras(set_name):
    """Get LoRA configuration for a specific set

    Returns list of LoRAs with their paths, weights, and metadata
    """
    try:
        # Security: Validate set_name
        if '..' in set_name or '/' in set_name or '\\' in set_name:
            return jsonify({'error': 'Invalid set name'}), 400

        set_config = get_set_config(set_name)
        if not set_config:
            return jsonify({'error': f'Set "{set_name}" not found'}), 404

        config = load_config()
        lora_base_dir = Path(config['model'].get('cache_dir', '/mnt/speedy/imagineer/models')) / 'lora'

        loras = []

        # Check if set has explicit 'loras' configuration
        if 'loras' in set_config and set_config['loras']:
            for lora_config in set_config['loras']:
                lora_path = Path(lora_config['path'])

                # Try to find this LoRA in the index to get metadata
                folder_name = lora_path.parent.name if lora_path.parent != lora_base_dir else None
                metadata = {}

                if folder_name:
                    index_path = lora_base_dir / 'index.json'
                    if index_path.exists():
                        with open(index_path, 'r') as f:
                            index = json.load(f)
                            if folder_name in index:
                                metadata = index[folder_name]

                loras.append({
                    'path': lora_config['path'],
                    'weight': lora_config.get('weight', 0.5),
                    'folder': folder_name,
                    'filename': lora_path.name,
                    'metadata': metadata
                })

        return jsonify({'loras': loras})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/sets/<set_name>/loras', methods=['PUT'])
def update_set_loras(set_name):
    """Update LoRA configuration for a specific set

    Expected JSON body:
    {
        "loras": [
            {"folder": "card_style", "weight": 0.6},
            {"folder": "tarot_theme", "weight": 0.4}
        ]
    }
    """
    try:
        # Security: Validate set_name
        if '..' in set_name or '/' in set_name or '\\' in set_name:
            return jsonify({'error': 'Invalid set name'}), 400

        data = request.json
        if not data or 'loras' not in data:
            return jsonify({'error': 'loras field is required'}), 400

        loras_config = data['loras']
        if not isinstance(loras_config, list):
            return jsonify({'error': 'loras must be a list'}), 400

        # Load main config
        config = load_config()
        lora_base_dir = Path(config['model'].get('cache_dir', '/mnt/speedy/imagineer/models')) / 'lora'

        # Convert folder names to full paths and validate
        loras_list = []
        for lora in loras_config:
            if not isinstance(lora, dict) or 'folder' not in lora:
                return jsonify({'error': 'Each LoRA must have a folder field'}), 400

            folder = lora['folder']
            weight = lora.get('weight', 0.5)

            # Validate weight
            try:
                weight = float(weight)
                if weight < 0 or weight > 2.0:
                    return jsonify({'error': f'Weight must be between 0 and 2.0, got {weight}'}), 400
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid weight value'}), 400

            # Find the .safetensors file in this folder
            lora_folder = lora_base_dir / folder
            if not lora_folder.exists():
                return jsonify({'error': f'LoRA folder "{folder}" not found'}), 404

            safetensors_files = list(lora_folder.glob('*.safetensors'))
            if not safetensors_files:
                return jsonify({'error': f'No .safetensors file found in folder "{folder}"'}), 404

            lora_path = safetensors_files[0]  # Use first .safetensors file

            loras_list.append({
                'path': str(lora_path),
                'weight': weight
            })

        # Load sets config
        if not SETS_CONFIG_PATH or not SETS_CONFIG_PATH.exists():
            return jsonify({'error': 'Sets configuration file not found'}), 404

        with open(SETS_CONFIG_PATH, 'r') as f:
            sets_config = yaml.safe_load(f) or {}

        if set_name not in sets_config:
            return jsonify({'error': f'Set "{set_name}" not found in configuration'}), 404

        # Update the loras configuration for this set
        sets_config[set_name]['loras'] = loras_list

        # Save updated config
        with open(SETS_CONFIG_PATH, 'w') as f:
            yaml.dump(sets_config, f, default_flow_style=False, sort_keys=False)

        return jsonify({
            'success': True,
            'message': f'Updated LoRA configuration for set "{set_name}"',
            'loras': loras_list
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    import os
    port = int(os.environ.get('FLASK_RUN_PORT', 10050))

    print("=" * 50)
    print("Imagineer API Server")
    print("=" * 50)
    print(f"Config: {CONFIG_PATH}")
    print(f"Output: {load_config()['output']['directory']}")
    print("")
    print(f"Starting server on http://0.0.0.0:{port}")
    print("Access from any device on your network!")
    print("=" * 50)

    app.run(host='0.0.0.0', port=port, debug=True)
