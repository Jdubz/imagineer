"""
Fine-tune Stable Diffusion using LoRA (Low-Rank Adaptation).
This is a memory-efficient method for fine-tuning on custom datasets.
"""

import argparse
import torch
from pathlib import Path
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
from diffusers.loaders import AttnProcsLayers
from diffusers.models.attention_processor import LoRAAttnProcessor
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from PIL import Image
import json
from tqdm import tqdm


class ImageCaptionDataset(Dataset):
    """Dataset for image-caption pairs."""

    def __init__(self, data_dir, size=512):
        self.data_dir = Path(data_dir)
        self.size = size
        self.image_paths = list(self.data_dir.glob("*.jpg")) + list(self.data_dir.glob("*.png"))

        self.transform = transforms.Compose([
            transforms.Resize(size, interpolation=transforms.InterpolationMode.BILINEAR),
            transforms.CenterCrop(size),
            transforms.ToTensor(),
            transforms.Normalize([0.5], [0.5])
        ])

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):
        image_path = self.image_paths[idx]
        image = Image.open(image_path).convert("RGB")

        # Look for caption in JSON or text file
        caption_path = image_path.with_suffix(".txt")
        if caption_path.exists():
            with open(caption_path, 'r') as f:
                caption = f.read().strip()
        else:
            # Fallback to filename as caption
            caption = image_path.stem.replace("_", " ")

        image = self.transform(image)
        return {"image": image, "caption": caption}


def main():
    parser = argparse.ArgumentParser(description="Fine-tune Stable Diffusion with LoRA")
    parser.add_argument(
        "--model",
        type=str,
        default="runwayml/stable-diffusion-v1-5",
        help="Base model to fine-tune"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        required=True,
        help="Directory containing training images and captions"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./checkpoints/lora",
        help="Directory to save LoRA weights"
    )
    parser.add_argument(
        "--rank",
        type=int,
        default=4,
        help="LoRA rank (lower = fewer parameters)"
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=1e-4,
        help="Learning rate"
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=1000,
        help="Number of training steps"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1,
        help="Training batch size"
    )
    parser.add_argument(
        "--save-steps",
        type=int,
        default=500,
        help="Save checkpoint every N steps"
    )

    args = parser.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")

    # Load the model
    print(f"Loading model: {args.model}")
    pipe = StableDiffusionPipeline.from_pretrained(
        args.model,
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        safety_checker=None
    )
    pipe = pipe.to(device)

    # Set up LoRA layers
    print(f"Setting up LoRA with rank {args.rank}")
    unet = pipe.unet
    lora_attn_procs = {}

    for name in unet.attn_processors.keys():
        cross_attention_dim = None if name.endswith("attn1.processor") else unet.config.cross_attention_dim
        if name.startswith("mid_block"):
            hidden_size = unet.config.block_out_channels[-1]
        elif name.startswith("up_blocks"):
            block_id = int(name[len("up_blocks.")])
            hidden_size = list(reversed(unet.config.block_out_channels))[block_id]
        elif name.startswith("down_blocks"):
            block_id = int(name[len("down_blocks.")])
            hidden_size = unet.config.block_out_channels[block_id]

        lora_attn_procs[name] = LoRAAttnProcessor(
            hidden_size=hidden_size,
            cross_attention_dim=cross_attention_dim,
            rank=args.rank
        )

    unet.set_attn_processor(lora_attn_procs)

    # Get trainable parameters
    lora_layers = AttnProcsLayers(unet.attn_processors)
    lora_layers.to(device, dtype=torch.float16 if device == "cuda" else torch.float32)

    # Set up optimizer
    optimizer = torch.optim.AdamW(lora_layers.parameters(), lr=args.learning_rate)

    # Load dataset
    print(f"Loading dataset from: {args.data_dir}")
    dataset = ImageCaptionDataset(args.data_dir)
    dataloader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True)

    print(f"Dataset size: {len(dataset)} images")

    # Training loop
    print("Starting training...")
    unet.train()
    global_step = 0

    progress_bar = tqdm(total=args.steps)

    while global_step < args.steps:
        for batch in dataloader:
            if global_step >= args.steps:
                break

            images = batch["image"].to(device)
            captions = batch["caption"]

            # Encode text
            text_inputs = pipe.tokenizer(
                captions,
                padding="max_length",
                max_length=pipe.tokenizer.model_max_length,
                truncation=True,
                return_tensors="pt"
            )
            text_embeddings = pipe.text_encoder(text_inputs.input_ids.to(device))[0]

            # Encode images
            latents = pipe.vae.encode(images).latent_dist.sample()
            latents = latents * pipe.vae.config.scaling_factor

            # Add noise
            noise = torch.randn_like(latents)
            timesteps = torch.randint(0, pipe.scheduler.config.num_train_timesteps, (latents.shape[0],), device=device)
            noisy_latents = pipe.scheduler.add_noise(latents, noise, timesteps)

            # Predict noise
            noise_pred = unet(noisy_latents, timesteps, text_embeddings).sample

            # Calculate loss
            loss = torch.nn.functional.mse_loss(noise_pred, noise)

            # Backward pass
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            global_step += 1
            progress_bar.update(1)
            progress_bar.set_postfix({"loss": loss.item()})

            # Save checkpoint
            if global_step % args.save_steps == 0:
                output_path = Path(args.output_dir) / f"checkpoint-{global_step}"
                output_path.mkdir(parents=True, exist_ok=True)
                lora_state_dict = {k: v for k, v in lora_layers.state_dict().items()}
                torch.save(lora_state_dict, output_path / "lora_weights.safetensors")
                print(f"\nCheckpoint saved to {output_path}")

    # Save final model
    output_path = Path(args.output_dir) / "final"
    output_path.mkdir(parents=True, exist_ok=True)
    lora_state_dict = {k: v for k, v in lora_layers.state_dict().items()}
    torch.save(lora_state_dict, output_path / "lora_weights.safetensors")
    print(f"\nFinal model saved to {output_path}")

    progress_bar.close()


if __name__ == "__main__":
    main()
