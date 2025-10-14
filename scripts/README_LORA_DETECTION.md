# LoRA Compatibility Detection

The `clean_loras.py` script uses **structural inspection** to detect incompatible LoRA formats, not just file size.

## Detection Techniques

### 1. **LyCORIS/Hadamard Detection**
**Pattern:** Looks for keys containing `hada_` prefix
- Keys like: `lora_unet_*.hada_w1_a`, `*.hada_w1_b`, `*.hada_w2_a`, `*.hada_w2_b`
- **Why incompatible:** Uses Hadamard product decomposition instead of standard LoRA adapter format
- **Library needed:** LyCORIS extension (not in standard diffusers)

**Example detected:**
- `TradingCard.safetensors` (22.3MB) - 1500 Hadamard keys
- `AnimePokerCard.safetensors` (23MB) - Hadamard format

### 2. **LoKr Detection**
**Pattern:** Looks for keys containing `lokr_` prefix
- Keys like: `*.lokr_w1`, `*.lokr_w2`
- **Why incompatible:** Uses Kronecker product factorization
- **Library needed:** LyCORIS extension

### 3. **SDXL Detection**
**Pattern:** Inspects tensor dimensions in UNet layers
- Samples `lora_unet_*_lora_down.weight` tensors
- Checks max dimension of tensor shapes
- **SD1.5:** Max dimensions typically < 1280
- **SDXL:** Max dimensions typically > 2048
- **Why incompatible:** Different UNet architecture, different base model needed

**File size hint (not relied upon):**
- SD1.5 LoRAs: Usually <150MB
- SDXL LoRAs: Usually ~218MB

### 4. **Standard SD1.5 (Compatible)**
**Pattern:** Has standard LoRA keys
- Keys like: `*.lora_up.weight`, `*.lora_down.weight`
- Keys prefixed with: `lora_unet_*`, `lora_te_*`
- Dimensions consistent with SD1.5 architecture

**Examples:**
- `Card_Fronts-000008.safetensors` - 528 LoRA keys
- `PlayingCard.safetensors` - 1972 LoRA keys
- `Tarot.safetensors` - 528 LoRA keys

## Usage

```bash
# Check only (dry run)
make lora-check

# Actually clean (moves to _incompatible/)
make lora-clean

# Custom directory
python scripts/clean_loras.py --lora-dir /path/to/loras

# Just report (no moving)
python scripts/clean_loras.py --no-move
```

## How It Works

1. **Opens safetensors file** using `safetensors` library (fast, no model loading)
2. **Reads key list** without loading full tensors into memory
3. **Pattern matching** on key names to detect format
4. **Dimension checking** by sampling a few tensors (lazy loading)
5. **Categorizes** as: sd15, lycoris, lokr, sdxl, unknown, or error
6. **Optionally moves** incompatible files to `_incompatible/` with format prefix

## Why This Approach?

- ✅ **Accurate** - Inspects actual structure, not just file size
- ✅ **Fast** - Only reads metadata and samples, doesn't load full model
- ✅ **Memory efficient** - Lazy tensor loading
- ✅ **Format-aware** - Detects LyCORIS, LoKr, SDXL, etc.
- ✅ **Safe** - Dry run by default, preserves originals in _incompatible/

## Current Results

After running `make lora-clean`:

```
card_deck/     (4 LoRAs - all compatible)
  ✓ Card_Fronts-000008.safetensors
  ✓ PlayingCard.safetensors
  ✓ carteSiciliane-sd15-lora.safetensors
  ✓ playing _card_face_v2.safetensors

tarot_deck/    (2 LoRAs - all compatible)
  ✓ Devil Carnival-000001.safetensors
  ✓ Tarot.safetensors

_incompatible/ (2 files moved)
  ✗ AnimePokerCard.safetensors (manually moved)
  ✗ lycoris_TradingCard.safetensors (auto-detected)
```

All remaining LoRAs are verified SD1.5 compatible and will auto-load!
