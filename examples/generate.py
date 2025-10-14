"""
Simplified image generation script that reads from config.yaml.
You only need to provide a prompt - all other settings come from config.
"""

import torch
import yaml
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
from pathlib import Path
import argparse
from datetime import datetime


def load_config(config_path="config.yaml"):
    """Load configuration from YAML file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser(
        description="Generate images with settings from config.yaml"
    )
    parser.add_argument(
        "--prompt",
        type=str,
        required=True,
        help="Text prompt for image generation"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output filename (auto-generated if not specified)"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.yaml",
        help="Path to config file"
    )
    # Allow overriding config values
    parser.add_argument("--steps", type=int, default=None)
    parser.add_argument("--width", type=int, default=None)
    parser.add_argument("--height", type=int, default=None)
    parser.add_argument("--guidance-scale", type=float, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--negative-prompt", type=str, default=None)
    parser.add_argument("--model", type=str, default=None)

    args = parser.parse_args()

    # Load config
    config = load_config(args.config)

    # Extract settings from config with command-line overrides
    model_id = args.model or config['model']['default']
    width = args.width or config['generation']['width']
    height = args.height or config['generation']['height']
    steps = args.steps or config['generation']['steps']
    guidance_scale = args.guidance_scale or config['generation']['guidance_scale']
    negative_prompt = args.negative_prompt or config['generation']['negative_prompt']

    # Auto-generate output filename if not specified
    if args.output is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Create safe filename from prompt (first 50 chars)
        prompt_slug = "".join(c if c.isalnum() or c in (' ', '-', '_') else ''
                             for c in args.prompt[:50]).strip().replace(' ', '_')
        output_dir = Path(config['output']['directory'])
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{timestamp}_{prompt_slug}.png"
    else:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

    # Check if CUDA is available
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")

    if device == "cpu":
        print("WARNING: Running on CPU. This will be very slow.")

    # Load the model
    print(f"Loading model: {model_id}")
    pipe = StableDiffusionPipeline.from_pretrained(
        model_id,
        dtype=torch.float16 if device == "cuda" else torch.float32,
        cache_dir=config['model'].get('cache_dir'),
        safety_checker=None
    )

    # Use DPM-Solver++ for faster inference
    pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
    pipe = pipe.to(device)

    # Enable memory optimizations from config
    if device == "cuda":
        if config['hardware'].get('enable_attention_slicing', True):
            pipe.enable_attention_slicing()
        if config['hardware'].get('enable_vae_slicing', False):
            pipe.enable_vae_slicing()

    # Set seed for reproducibility
    generator = None
    if args.seed is not None:
        generator = torch.Generator(device=device).manual_seed(args.seed)
        print(f"Using seed: {args.seed}")

    # Display generation settings
    print(f"\nGeneration Settings:")
    print(f"  Prompt: '{args.prompt}'")
    print(f"  Negative: '{negative_prompt}'")
    print(f"  Size: {width}x{height}")
    print(f"  Steps: {steps}")
    print(f"  Guidance Scale: {guidance_scale}")
    print(f"  Output: {output_path}\n")

    # Generate image
    print("Generating image...")
    image = pipe(
        prompt=args.prompt,
        negative_prompt=negative_prompt,
        num_inference_steps=steps,
        guidance_scale=guidance_scale,
        generator=generator,
        width=width,
        height=height
    ).images[0]

    # Save the image
    image.save(output_path)
    print(f"✓ Image saved to: {output_path}")

    # Save metadata if enabled
    if config['output'].get('save_metadata', False):
        metadata = {
            'prompt': args.prompt,
            'negative_prompt': negative_prompt,
            'model': model_id,
            'width': width,
            'height': height,
            'steps': steps,
            'guidance_scale': guidance_scale,
            'seed': args.seed,
            'timestamp': datetime.now().isoformat()
        }

        import json
        metadata_path = output_path.with_suffix('.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        print(f"✓ Metadata saved to: {metadata_path}")


if __name__ == "__main__":
    main()
