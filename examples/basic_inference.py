"""
Basic Stable Diffusion inference example.
This script demonstrates how to generate images using Stable Diffusion models.
"""

import torch
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
from pathlib import Path
import argparse


def main():
    parser = argparse.ArgumentParser(description="Generate images using Stable Diffusion")
    parser.add_argument(
        "--prompt",
        type=str,
        required=True,
        help="Text prompt for image generation"
    )
    parser.add_argument(
        "--negative-prompt",
        type=str,
        default="blurry, low quality, distorted",
        help="Negative prompt to guide what to avoid"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="runwayml/stable-diffusion-v1-5",
        help="Model ID from Hugging Face or local path"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="outputs/generated.png",
        help="Output path for generated image"
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=25,
        help="Number of inference steps"
    )
    parser.add_argument(
        "--guidance-scale",
        type=float,
        default=7.5,
        help="Guidance scale (higher = more adherence to prompt)"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducibility"
    )
    parser.add_argument(
        "--width",
        type=int,
        default=512,
        help="Image width"
    )
    parser.add_argument(
        "--height",
        type=int,
        default=512,
        help="Image height"
    )

    args = parser.parse_args()

    # Check if CUDA is available
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")

    if device == "cpu":
        print("WARNING: Running on CPU. This will be very slow. Install CUDA-enabled PyTorch for GPU acceleration.")

    # Load the model
    print(f"Loading model: {args.model}")
    pipe = StableDiffusionPipeline.from_pretrained(
        args.model,
        dtype=torch.float16 if device == "cuda" else torch.float32,
        safety_checker=None  # Remove for faster inference
    )

    # Use DPM-Solver++ for faster inference
    pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)

    pipe = pipe.to(device)

    # Enable memory optimizations
    if device == "cuda":
        pipe.enable_attention_slicing()
        # Uncomment if you have memory issues:
        # pipe.enable_vae_slicing()
        # pipe.enable_xformers_memory_efficient_attention()

    # Set seed for reproducibility
    generator = None
    if args.seed is not None:
        generator = torch.Generator(device=device).manual_seed(args.seed)
        print(f"Using seed: {args.seed}")

    # Generate image
    print(f"Generating image with prompt: '{args.prompt}'")
    image = pipe(
        prompt=args.prompt,
        negative_prompt=args.negative_prompt,
        num_inference_steps=args.steps,
        guidance_scale=args.guidance_scale,
        generator=generator,
        width=args.width,
        height=args.height
    ).images[0]

    # Save the image
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)
    print(f"Image saved to: {output_path}")


if __name__ == "__main__":
    main()
