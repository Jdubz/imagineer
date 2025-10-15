# LoRA Organization System

Automated system for organizing, testing, and indexing LoRA models.

## Overview

Drop new LoRA files in `/mnt/speedy/imagineer/models/lora/` and run `make lora-organize` to:

1. ✅ **Test compatibility** (SD1.5, LyCORIS, SDXL detection)
2. 🗑️ **Auto-remove incompatible** (moves to `_incompatible/`)
3. 📁 **Create dedicated folder** for each LoRA
4. 🖼️ **Generate preview image** (640x640, full weight)
5. ⚙️ **Create config file** (name, weight, metadata)
6. 📋 **Update index** (JSON database)
7. ✔️ **Reconcile & validate** (ensure sync)

## Quick Start

### Two-Step Workflow (Recommended)

```bash
# Step 1: Drop LoRA files in /mnt/speedy/imagineer/models/lora/
cp ~/Downloads/*.safetensors /mnt/speedy/imagineer/models/lora/

# Step 2: Organize (fast - no previews)
make lora-organize-fast

# Step 3: Start API server (in another terminal)
python server/api.py

# Step 4: Queue preview generation
make lora-previews-queue

# Step 5: Monitor progress
curl http://localhost:10050/api/jobs
# Or visit http://localhost:3000 and check Generate tab
```

### One-Step Workflow (Simple)

```bash
# 1. Drop LoRA files
cp ~/Downloads/*.safetensors /mnt/speedy/imagineer/models/lora/

# 2. Organize with local preview generation (may be slow)
make lora-organize

# 3. Check results
make lora-reconcile
```

## Commands

### Organization Commands

#### `make lora-check`
Check LoRA compatibility without moving files (dry run)

#### `make lora-clean`
Move existing incompatible LoRAs to `_incompatible/`

#### `make lora-organize`
**Full organization** - Organize new LoRAs with local preview generation:
- Tests each LoRA for compatibility
- Moves incompatible to `_incompatible/`
- Creates folder + config for compatible ones
- Generates previews locally (synchronous, may timeout)
- Updates index.json
- Validates sync

#### `make lora-organize-fast`
**Fast organization** - Organize without preview generation:
- Tests each LoRA for compatibility
- Moves incompatible to `_incompatible/`
- Creates folder + config for compatible ones
- Updates index.json
- Validates sync
- **Recommended** for initial organization

#### `make lora-reconcile`
Validate index against folders (no changes, just checks)

### Preview Generation Commands

#### `make lora-previews-queue`
**Queue preview generation** - Submit preview jobs to API server:
- Requires API server running (`python server/api.py`)
- Queues jobs for LoRAs missing previews
- Returns immediately, jobs process in background
- Monitor: `curl http://localhost:10050/api/jobs`
- **Recommended** for bulk preview generation

#### `make lora-previews`
**Local preview generation** - Generate previews synchronously:
- Generates previews for LoRAs missing them
- Runs locally (may be slow)
- Good for generating 1-2 previews

## Directory Structure

```
/mnt/speedy/imagineer/models/lora/
├── preview_config.json           # Global preview settings
├── index.json                    # Master index (auto-maintained)
├── t4r0th/                       # Auto-created folder
│   ├── T4R0TH.safetensors       # LoRA file
│   ├── config.yaml              # Metadata
│   └── preview.png              # Preview image (640x640)
├── queen_of_hearts/
│   ├── Queen_of_Hearts.safetensors
│   ├── config.yaml
│   └── preview.png
└── _incompatible/               # Rejected LoRAs
    ├── lycoris_AnimePokerCard.safetensors
    └── sdxl_LS.safetensors
```

## Config File Format

Each LoRA folder gets a `config.yaml`:

```yaml
name: T4R0Th                      # Display name (auto-generated)
filename: T4R0TH.safetensors      # Original filename
default_weight: 0.6               # Recommended weight
preview_image: preview.png        # Preview path (relative)
created: '2025-10-13T23:29:18'    # Timestamp
compatible: sd15                  # Format type
notes: 'TODO: Add description'    # User-editable notes
```

## Index File Format

`index.json` tracks all organized LoRAs:

```json
{
  "t4r0th": {
    "filename": "T4R0TH.safetensors",
    "folder": "t4r0th",
    "compatible": true,
    "format": "sd15",
    "has_preview": true,
    "has_config": true,
    "organized_at": "2025-10-13T23:29:18.166645"
  }
}
```

## Preview Generation

Previews are generated automatically with:
- **Size:** 640×640
- **Prompt:** "jester, high quality, detailed, professional"
- **Negative prompt:** Uses the same negative prompt from `config.yaml` (ensures consistent quality)
- **Weight:** 1.0 (full strength)
- **Steps:** 20

**TODO:** Implement smart prompts based on LoRA name/type

The negative prompt is automatically loaded from your main `config.yaml` generation settings, ensuring preview quality matches your batch generation quality standards.

### Skip Previews (Faster)

```bash
python scripts/organize_loras.py --no-preview
```

## Compatibility Detection

The system detects:

### ✅ Compatible (SD1.5)
- Standard LoRA keys: `*.lora_up.weight`, `*.lora_down.weight`
- Typical size: <150MB
- Example: 528-1972 LoRA keys

### ❌ Incompatible

**LyCORIS/Hadamard:**
- Keys contain `hada_w1_a`, `hada_w2_b`, etc.
- Requires LyCORIS extension

**LoKr:**
- Keys contain `lokr_*`
- Kronecker factorization format

**SDXL:**
- Tensor dimensions > 2048
- Requires SDXL base model
- Typical size: ~218MB (but not always!)

## Reconciliation

Ensures index stays in sync with folders:

**Checks:**
- ✅ All indexed folders exist on disk
- ✅ All folders have config.yaml
- ✅ All folders contain .safetensors file
- ⚠️ Warns about unindexed folders
- ❌ Errors on missing folders or files

**Run after:**
- Manual file operations
- Moving folders
- Deleting LoRAs

## Workflow Example

```bash
# Download new LoRAs
cd /mnt/speedy/imagineer/models/lora/
wget https://example.com/cool_lora.safetensors

# Organize (test + folder + preview + index)
make lora-organize

# Output:
# Processing: cool_lora.safetensors
#   ✓ Compatible: Standard SD1.5 LoRA (528 keys)
#   ✓ Created folder: cool_lora/
#   ✓ Moved file into folder
#   ✓ Generating preview... ✓
#   ✓ Created config.yaml
#   ✓ Added to index
# ✓ Organization complete!

# Verify
make lora-reconcile

# Edit config if needed
vi cool_lora/config.yaml
```

## Advanced Options

### Custom LoRA Directory

```bash
python scripts/organize_loras.py --lora-dir /custom/path
```

### Reconcile Only

```bash
python scripts/organize_loras.py --reconcile-only
```

### Skip Preview Generation

```bash
python scripts/organize_loras.py --no-preview
```

## Integration

The organization system works alongside:

- **Set-based folders** (`card_deck/`, `tarot_deck/`) - Still work with dynamic discovery
- **Index file** - Can be queried by web UI for LoRA gallery
- **Config files** - Provide metadata for each LoRA

## Best Practices

1. **Always run `lora-organize`** after downloading new LoRAs
2. **Check index** regularly with `lora-reconcile`
3. **Edit config notes** to describe each LoRA's purpose
4. **Delete from index** if you manually remove folders
5. **Backup index.json** before major changes

## Troubleshooting

### "Folder not in index"
Run `lora-organize` to add it, or manually add to index.json

### "Missing config.yaml"
Regenerate with:
```bash
rm -rf problem_folder/
cp problem_folder.safetensors /mnt/speedy/imagineer/models/lora/
make lora-organize
```

### "Preview generation failed"
- Check VRAM availability
- Try `--no-preview` flag
- Manually generate later

### "Index out of sync"
```bash
# Fix automatically
make lora-organize
make lora-reconcile
```

## Files

- `scripts/organize_loras.py` - Main organization script
- `scripts/generate_previews.py` - Preview generation script
- `scripts/clean_loras.py` - Compatibility checker
- `/mnt/speedy/imagineer/models/lora/index.json` - Master index
- `/mnt/speedy/imagineer/models/lora/preview_config.json` - Global preview settings

## Preview Configuration (v2)

Preview generation settings are stored globally in `preview_config.json`:

```json
{
  "prompt": "jester",
  "full_prompt": "jester, high quality, detailed, professional",
  "width": 640,
  "height": 640,
  "steps": 30,
  "guidance_scale": 8.0,
  "weight": 1.0,
  "negative_prompt_source": "config.yaml",
  "note": "All previews use these settings for consistency"
}
```

### Preview Config Fields

- **prompt** - Base prompt used ("jester")
- **full_prompt** - Complete prompt with enhancements
- **width/height** - Preview dimensions (640×640)
- **steps** - Generation steps (30 for high quality)
- **guidance_scale** - CFG scale (8.0 for strict adherence)
- **weight** - LoRA strength (1.0 = full weight)
- **negative_prompt_source** - Where negative prompt came from

### Why Separate File?

- **Clarity** - Preview settings separated from LoRA metadata
- **Consistency** - All previews use identical settings
- **Easy to update** - Change settings in one place
- **Clean structure** - Index remains purely for LoRA metadata

This ensures every preview is:
- **Reproducible** - Settings are documented
- **High quality** - 30 steps with guidance 8.0
- **Consistent** - Uses project negative prompt standards
- **Documented** - Can see exactly how it was generated

### Regenerating Previews

To regenerate previews with updated settings:

```bash
# Update preview_config.json settings
nano /mnt/speedy/imagineer/models/lora/preview_config.json

# Delete existing previews
find /mnt/speedy/imagineer/models/lora/*/preview.png -delete

# Move LoRAs back to root and re-organize
for lora in /mnt/speedy/imagineer/models/lora/*/*.safetensors; do
  mv "$lora" /mnt/speedy/imagineer/models/lora/
done
rm -rf /mnt/speedy/imagineer/models/lora/*/
rm /mnt/speedy/imagineer/models/lora/index.json

# Re-organize with previews
make lora-organize
```
