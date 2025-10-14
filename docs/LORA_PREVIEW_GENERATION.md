# LoRA Preview Generation with Auto-Detected Trigger Words

## Overview

LoRA preview images are now generated using automatically extracted trigger words from the LoRA filename, rather than generic prompts. This produces previews that better showcase each LoRA's trained content.

## How It Works

### Trigger Word Extraction

The system automatically extracts trigger words from LoRA filenames using these rules:

1. **Remove file extensions** (`.safetensors`)
2. **Remove version patterns**: `-000001`, `_V2`, `-v3`, etc.
3. **Split camelCase**: `CelestialTarot` → `Celestial Tarot`
4. **Replace underscores/hyphens with spaces**
5. **Clean up multiple spaces**
6. **Convert to lowercase**

### Examples

| Filename | Extracted Trigger Words |
|----------|------------------------|
| `Devil Carnival-000001.safetensors` | `devil carnival` |
| `Card_Fronts-000008.safetensors` | `card fronts` |
| `CelestialTarot_V2.safetensors` | `celestial tarot` |
| `Balatro_poker_cards.safetensors` | `balatro poker cards` |
| `jojo_tarot.safetensors` | `jojo tarot` |

### Prompt Construction

Final prompt format: `"<trigger_words>, high quality, detailed, professional"`

For example:
- Trigger words: `"devil carnival"`
- Full prompt: `"devil carnival, high quality, detailed, professional"`

## Usage

### Test Trigger Word Extraction (Dry Run)

See what prompts will be generated without creating any images:

```bash
make lora-previews-test
```

Or directly:

```bash
python scripts/test_trigger_words.py
```

### Organize New LoRAs (Auto-Detection Enabled)

When organizing new LoRAs, trigger words are automatically extracted:

```bash
# With preview generation
make lora-organize

# Without previews (organize only)
make lora-organize-fast

# Then generate previews via API queue
make lora-previews-queue
```

### Regenerate All Existing Previews

Replace all existing previews with new ones using auto-detected trigger words:

```bash
# Recommended: Queue via API (runs async)
make lora-previews-regenerate
```

Or directly:

```bash
# Via API queue (async)
python scripts/regenerate_previews.py --queue

# Locally (synchronous, slower)
python scripts/regenerate_previews.py
```

⚠️ **Warning**: This will replace ALL existing preview images!

## Manual Override

To use a custom prompt for a specific LoRA's preview, you can manually specify it:

```bash
# Generate with custom prompt
python scripts/generate_previews.py --lora devil_carnival-000001
# Then manually edit the script to pass a custom prompt parameter
```

Or edit the LoRA's `config.yaml` to add:

```yaml
# models/lora/devil_carnival-000001/config.yaml
name: Devil Carnival-000001
preview_prompt: "ornate playing card, mystical carnival theme"
```

(Note: Manual override via config.yaml is not yet implemented, but planned)

## File Locations

- **Extraction logic**: `scripts/organize_loras.py::extract_trigger_words()`
- **Test script**: `scripts/test_trigger_words.py`
- **Regeneration script**: `scripts/regenerate_previews.py`
- **Preview generation**: `scripts/generate_previews.py`

## Technical Details

### Why Not Use Empty Prompts?

Empty prompts don't work well with Stable Diffusion 1.5. Even with a LoRA applied, the base model needs textual guidance to understand *what* to generate. The LoRA only modifies *how* it generates, not *what* to generate.

### Why Not Manual Trigger Words?

Manual trigger words require maintaining a `trigger_words` field in each LoRA's `config.yaml`. This doesn't scale well for large collections. Filename-based extraction provides:

- **Zero manual effort**: Works immediately for all LoRAs
- **Reproducible**: Same filename always produces same trigger words
- **Descriptive filenames**: Most LoRA creators use descriptive names
- **Easy to override**: Can still add manual prompts when needed

### Preview Settings

All previews use consistent settings for comparability:

```yaml
width: 640
height: 640
steps: 30
guidance_scale: 8.0
lora_weight: 1.0
prompt_template: "<trigger_words>, high quality, detailed, professional"
```

Negative prompt is inherited from `config.yaml::generation.negative_prompt`.

## Future Enhancements

Planned improvements:

1. **Config override**: Support `preview_prompt` field in LoRA config.yaml
2. **Metadata inspection**: Extract trigger words from safetensors metadata if available
3. **CivitAI integration**: Fetch trigger words from CivitAI API by model hash
4. **Better version detection**: Improve regex to handle edge cases like `Tarotv0.2`
5. **Batch regeneration with filters**: Regenerate only specific categories or LoRAs

## Troubleshooting

### Trigger words don't match LoRA content

If the filename-based extraction produces poor trigger words, you can:

1. Rename the LoRA file to better describe its content
2. Run `make lora-organize` to reorganize it
3. Regenerate the preview

### Preview shows wrong content

Some LoRAs require specific activation tokens that aren't in the filename. In this case:

1. Check the LoRA's documentation on CivitAI
2. Add a manual `preview_prompt` to the config.yaml (when implemented)
3. Or rename the LoRA file to include the activation token

### All previews show similar content

This indicates the negative prompt might be too restrictive, or the trigger words are too generic. Consider:

1. Adjusting the negative prompt in `config.yaml`
2. Adding more descriptive terms to the LoRA filename
3. Lowering the LoRA weight (currently 1.0 for previews)
