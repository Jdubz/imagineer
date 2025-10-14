# LoRA Organization Script - Technical Details

## Preview Generation with Config Integration

The `organize_loras.py` script now integrates with your main `config.yaml` to ensure consistent quality across all generations.

### Negative Prompt Usage

When generating preview images, the script:

1. **Loads** `config.yaml` from project root
2. **Extracts** `generation.negative_prompt` setting
3. **Passes** it to `examples/generate.py` via `--negative-prompt` flag
4. **Ensures** previews use the same quality standards as batch generation

### Example Flow

```python
# Script loads config
config = load_config()  # From config.yaml

# Extracts negative prompt
negative_prompt = config['generation'].get('negative_prompt')

# Passes to generation
generate_preview(
    lora_path=lora_file,
    output_path=preview_path,
    prompt="joker, high quality, detailed, professional",
    negative_prompt=negative_prompt,  # ← Uses your config!
    weight=1.0,
    width=640,
    height=640,
    steps=20
)
```

### Your Current Negative Prompt

From `config.yaml`:
```
blurry, low quality, low resolution, low detail, poorly drawn,
bad anatomy, bad proportions, bad composition, distorted, deformed, 
disfigured, ugly, unattractive, gross, disgusting, mutation, mutated,
extra limbs, extra legs, extra arms, extra fingers, extra hands, 
missing limbs, missing legs, missing arms, missing fingers, 
fused limbs, fused fingers, fused toes, cloned face, duplicate...
[full comprehensive negative prompt]
```

This ensures preview images avoid all the same quality issues as your production generations!

### Benefits

✅ **Consistent quality** - Previews match production output  
✅ **No duplicate config** - Single source of truth  
✅ **Auto-updates** - Change config once, affects all previews  
✅ **Comprehensive** - Uses your carefully crafted negative prompt

### Fallback Behavior

If `config.yaml` cannot be loaded:
- Script prints: `Warning: Could not load config.yaml, using defaults`
- Continues without negative prompt
- Still generates previews (just without the negative filtering)

### Testing

To verify the integration:

```bash
# Check what negative prompt is loaded
python -c "
import sys
sys.path.insert(0, 'scripts')
from organize_loras import load_config
config = load_config()
print(config['generation']['negative_prompt'][:200])
"

# Run organization and check preview command
make lora-organize
# Look for: --negative-prompt in the generation output
```

## Future Enhancements

### Smart Prompts (TODO)

The prompt could be improved to match LoRA type:

```python
def get_smart_prompt(lora_name, lora_folder):
    """Generate appropriate prompt based on LoRA type"""
    name_lower = lora_name.lower()

    if 'tarot' in name_lower:
        return "tarot card, mystical, arcana, symbolic"
    elif 'card' in name_lower or 'playing' in name_lower:
        return "playing card, card game, single card"
    elif 'portrait' in name_lower or 'face' in name_lower:
        return "portrait, face, character"
    elif 'landscape' in name_lower:
        return "landscape, scenery, environment"
    else:
        return "joker"  # Neutral fallback
```

This would create more relevant previews automatically!

## Configuration Priority

The script respects this priority:

1. **Main config** (`config.yaml`) - For negative prompt, defaults
2. **Command line args** - For overrides (--no-preview, etc.)
3. **Per-LoRA config** - Generated after organization (config.yaml in folder)

Each LoRA's individual `config.yaml` stores metadata but doesn't affect generation - it's for documentation and future UI features.
