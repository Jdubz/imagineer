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
DATA_SETS_DIR = PROJECT_ROOT / 'data' / 'sets'

# Job queue
job_queue = queue.Queue()
job_history = []
current_job = None


def load_config():
    """Load config.yaml"""
    with open(CONFIG_PATH, 'r') as f:
        return yaml.safe_load(f)


def save_config(config):
    """Save config.yaml"""
    with open(CONFIG_PATH, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)


def load_set_data(set_name):
    """Load data from a CSV set file

    Args:
        set_name: Name of the set (without .csv extension)

    Returns:
        List of dicts with 'name' and 'description' keys

    Raises:
        FileNotFoundError: If set doesn't exist
        ValueError: If CSV is malformed
    """
    # Security: Validate set_name to prevent path traversal
    if '..' in set_name or '/' in set_name or '\\' in set_name:
        raise ValueError('Invalid set name')

    set_path = DATA_SETS_DIR / f"{set_name}.csv"

    if not set_path.exists():
        raise FileNotFoundError(f'Set "{set_name}" not found')

    items = []
    with open(set_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        # Validate CSV has required columns
        if 'name' not in reader.fieldnames or 'description' not in reader.fieldnames:
            raise ValueError('CSV must have "name" and "description" columns')

        for row in reader:
            items.append({
                'name': row['name'].strip(),
                'description': row['description'].strip()
            })

    if not items:
        raise ValueError('Set is empty')

    return items


def list_available_sets():
    """List all available CSV sets

    Returns:
        List of set names (without .csv extension)
    """
    if not DATA_SETS_DIR.exists():
        return []

    sets = []
    for csv_file in DATA_SETS_DIR.glob('*.csv'):
        sets.append(csv_file.stem)

    return sorted(sets)


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

            # For batch jobs, specify output directory
            if job.get('output_dir') and job.get('batch_item_name'):
                # Create sanitized filename from batch item name
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

        job = {
            'id': len(job_history) + job_queue.qsize() + 1,
            'prompt': prompt,
            'seed': seed,
            'steps': steps,
            'width': width,
            'height': height,
            'guidance_scale': guidance_scale,
            'negative_prompt': negative_prompt,
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
    """List available CSV sets"""
    try:
        sets = list_available_sets()
        return jsonify({'sets': sets})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/generate/batch', methods=['POST'])
def generate_batch():
    """Submit batch generation from CSV set

    Creates multiple jobs by combining set data with a prompt template.
    All images will be saved in a subfolder named after the batch.
    """
    try:
        data = request.json

        if not data or not data.get('set_name'):
            return jsonify({'error': 'set_name is required'}), 400

        if not data.get('prompt_template'):
            return jsonify({'error': 'prompt_template is required'}), 400

        set_name = str(data['set_name']).strip()
        prompt_template = str(data['prompt_template']).strip()

        if not prompt_template:
            return jsonify({'error': 'prompt_template cannot be empty'}), 400

        if len(prompt_template) > 2000:
            return jsonify({'error': 'prompt_template too long (max 2000 chars)'}), 400

        # Load set data
        try:
            set_items = load_set_data(set_name)
        except FileNotFoundError:
            return jsonify({'error': f'Set "{set_name}" not found'}), 404
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

        # Create jobs for each item in the set
        job_ids = []
        for item in set_items:
            # Combine template with item description
            # Template can use {name} and {description} placeholders
            prompt = prompt_template.replace('{name}', item['name'])
            prompt = prompt.replace('{description}', item['description'])

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
                'batch_item_name': item['name'],
                'output_dir': str(batch_output_dir)  # Custom output directory for this job
            }

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


@app.route('/api/outputs', methods=['GET'])
def list_outputs():
    """List generated images"""
    try:
        config = load_config()
        output_dir = Path(config['output']['directory'])

        images = []
        if output_dir.exists():
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
        # Remove any directory traversal attempts
        safe_filename = os.path.basename(filename)

        # Construct the full path and resolve it
        requested_path = (output_dir / safe_filename).resolve()

        # Security check: Ensure the resolved path is within output_dir
        if not str(requested_path).startswith(str(output_dir)):
            return jsonify({'error': 'Access denied'}), 403

        # Check if file exists and is a file (not a directory)
        if not requested_path.exists() or not requested_path.is_file():
            return jsonify({'error': 'File not found'}), 404

        return send_from_directory(output_dir, safe_filename)

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
