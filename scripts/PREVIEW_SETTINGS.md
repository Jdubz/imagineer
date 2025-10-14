# Preview Generation Settings

## Overview

All LoRA preview images are generated with consistent, high-quality settings stored in a dedicated configuration file.

## Global Configuration Storage

The preview settings are stored in `/mnt/speedy/imagineer/models/lora/preview_config.json`:

```json
{
  "prompt": "joker",
  "full_prompt": "joker, high quality, detailed, professional",
  "width": 640,
  "height": 640,
  "steps": 30,
  "guidance_scale": 8.0,
  "weight": 1.0,
  "negative_prompt_source": "config.yaml",
  "note": "All previews use these settings for consistency"
}
```

### Why Separate Config File?

- **Clarity** - Preview settings separated from LoRA metadata
- **Consistency** - All previews use identical settings, making them comparable
- **Single source of truth** - One config applies to all LoRAs
- **Easy to update** - Change settings in one place without modifying index
- **Clean structure** - Index remains purely for LoRA metadata
- **Reproducibility** - Settings are documented and versioned

## Current Generation Settings

### Resolution
- **640×640** - Square format perfect for UI thumbnails
- Higher than typical 512×512
- Lower than production 512×720
- Good balance of quality vs generation time

### Prompt
- **Base:** `"joker"`
- **Full:** `"joker, high quality, detailed, professional"`

#### Why "joker"?
- **Neutral** - Works across all LoRA types (cards, tarot, portraits)
- **Simple** - Easy to compare LoRA effects without prompt bias
- **Recognizable** - Familiar subject for visual evaluation
- **Not style-specific** - Doesn't bias toward one art style

### Generation Parameters

**Steps: 30** (High Quality)
- Standard generation: 20-25 steps
- Preview generation: **30 steps** for better quality
- Trade-off: Slower generation but cleaner output
- Ensures preview accurately represents LoRA capability

**Guidance Scale: 8.0** (Strict Adherence)
- Standard range: 7.0-9.0
- Preview uses: **8.0** for balanced adherence
- Higher = more prompt adherence
- Lower = more creative freedom
- 8.0 provides consistent, predictable results

**LoRA Weight: 1.0** (Full Strength)
- Shows LoRA at **maximum strength**
- Users can evaluate full effect
- Can be reduced in actual usage (typical: 0.4-0.8)
- Preview demonstrates "what this LoRA adds"

### Negative Prompt

Uses the comprehensive negative prompt from main `config.yaml`:
```
blurry, low quality, low resolution, low detail, poorly drawn,
bad anatomy, bad proportions, bad composition, distorted, deformed,
disfigured, ugly, unattractive, gross, disgusting, mutation, mutated,
extra limbs, extra legs, extra arms, extra fingers, extra hands,
missing limbs, missing legs, missing arms, missing fingers,
fused limbs, fused fingers, fused toes, cloned face, duplicate...
[1739 characters total]
```

#### Why Use Project Negative Prompt?

✅ **Consistent quality** - Previews match production output
✅ **No duplicate config** - Single source of truth
✅ **Auto-updates** - Change config once, affects all previews
✅ **Comprehensive** - Uses carefully crafted negative prompt

## How It Works

### Organization Flow

1. **New LoRA detected** in `/mnt/speedy/imagineer/models/lora/`
2. **Compatibility tested** (SD1.5, LyCORIS, SDXL detection)
3. **Folder created** for compatible LoRA
4. **Preview generated** using settings from `_preview_config`
5. **Negative prompt loaded** from main `config.yaml`
6. **Config file created** in LoRA folder
7. **Index updated** with LoRA entry
8. **Global preview config** saved or preserved in index

### Generation Command

```bash
venv/bin/python examples/generate.py \
  --prompt "joker, high quality, detailed, professional" \
  --lora-paths /path/to/lora.safetensors \
  --lora-weights 1.0 \
  --width 640 \
  --height 640 \
  --steps 30 \
  --guidance-scale 8.0 \
  --negative-prompt "<loaded from config.yaml>" \
  --output /path/to/preview.png
```

## Implementation Details

### organize_loras.py Integration

**save_preview_config() function** (lines 78-93):
```python
def save_preview_config(lora_base_dir, preview_config):
    """Save global preview config to separate file"""
    preview_config_path = lora_base_dir / 'preview_config.json'

    with open(preview_config_path, 'w') as f:
        json.dump(preview_config, f, indent=2)
```

**load_preview_config() function** (lines 96-123):
```python
def load_preview_config(lora_base_dir):
    """Load global preview config from separate file

    Returns default config if file doesn't exist
    """
    preview_config_path = lora_base_dir / 'preview_config.json'

    default_config = {
        'prompt': 'joker',
        'full_prompt': 'joker, high quality, detailed, professional',
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
    except Exception:
        return default_config
```

**save_index() function** (lines 126-144):
```python
def save_index(lora_base_dir, index):
    """Save the LoRA index file

    Index contains only LoRA metadata, no preview config
    """
    index_path = lora_base_dir / 'index.json'

    # Save index sorted by key for consistency
    sorted_index = {k: index[k] for k in sorted(index.keys())}

    with open(index_path, 'w') as f:
        json.dump(sorted_index, f, indent=2)
```

**generate_preview() function** (lines 192-266):
- Loads negative prompt from main `config.yaml`
- Generates preview with high-quality settings
- Returns tuple: `(success: bool, preview_config: dict)`
- Preview config saved separately via `save_preview_config()`

### File Structure

```
/mnt/speedy/imagineer/models/lora/
├── preview_config.json          # Global preview settings
├── index.json                   # LoRA metadata only
├── lora_name_1/
│   ├── lora.safetensors
│   ├── config.yaml
│   └── preview.png
└── lora_name_2/
    ├── lora.safetensors
    ├── config.yaml
    └── preview.png
```

## Usage

### Organize New LoRAs

```bash
# Full organization with previews
make lora-organize

# Skip preview generation (faster)
python scripts/organize_loras.py --no-preview

# Reconcile only (no new organization)
make lora-reconcile
```

### Verify Preview Config

```bash
# View current preview config
cat /mnt/speedy/imagineer/models/lora/preview_config.json

# Or with Python
python3 -c "import json; print(json.dumps(json.load(open('/mnt/speedy/imagineer/models/lora/preview_config.json')), indent=2))"
```

### Update Preview Config

Edit `/mnt/speedy/imagineer/models/lora/preview_config.json` directly:

```bash
# Edit with your preferred editor
nano /mnt/speedy/imagineer/models/lora/preview_config.json

# Changes apply to all future preview generations
```

## Future Enhancements

### Smart Prompts (TODO)

Automatically select appropriate prompt based on LoRA name/type:

```python
def get_smart_prompt(lora_name):
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

### Multiple Previews per LoRA

Generate preview grid showing:
- Different prompts (tarot-specific, card-specific, generic)
- Different weights (0.5, 0.8, 1.0)
- Weight progression comparison

### Per-Set Preview Config

Allow sets to define custom preview settings in `/mnt/speedy/imagineer/sets/config.yaml`:

```yaml
card_deck:
  preview_config:
    prompt: "playing card, ace of spades"
    steps: 30
    guidance_scale: 8.0
```

## Benefits

✅ **Consistent** - All previews use identical settings
✅ **Reproducible** - Settings documented in index
✅ **High quality** - 30 steps with strict guidance
✅ **Comparable** - Easy to evaluate different LoRAs side-by-side
✅ **Documented** - Know exactly how each preview was generated
✅ **Single source** - One config applies to all LoRAs
✅ **Auto-maintained** - Scripts preserve and update config automatically
