# Training Data

Place your training images here for fine-tuning models.

## File Structure

For each training image, you should have:
- An image file (`.jpg`, `.png`)
- A caption file with the same name (`.txt`)

Example:
```
data/training/
├── image001.jpg
├── image001.txt
├── image002.png
├── image002.txt
└── ...
```

## Caption Format

Each `.txt` file should contain a single line describing the image:

```
a photograph of a red sports car on a mountain road at sunset
```

## Tips

- Use consistent caption styles across your dataset
- Include relevant details in captions
- 10-100 images is often enough for LoRA fine-tuning
- Higher quality images lead to better results
- Use similar resolution images (512x512 or 1024x1024)

## Data Sources

Consider these sources for training data:
- Your own photographs
- Public domain images
- Creative Commons licensed images
- Generated images from other models

Always respect copyright and licensing requirements.
