# LoRA Setup Guide - Playing Cards

## ✅ What's Been Done

### 1. Enhanced Visual Descriptions
- Updated `card_deck.csv` with explicit visual layouts for all 54 cards
- Each card now specifies: pip count, arrangement, corner values, colors
- Example: "Five black spade symbols: four in corners of inner area plus one large in center. Number 5 in all four corners with small spade pips"

### 2. LoRA Integration
- Added LoRA support to `examples/generate.py`
- New command-line options: `--lora-path` and `--lora-weight`
- API automatically passes LoRA parameters from set configuration

### 3. Configuration Updates
- Updated `card_deck` config with:
  - "PlayingCards" trigger word in base_prompt
  - LoRA path and weight settings
  - Enhanced negative prompts to prevent card stacks

## 🔽 What You Need To Do: Download the LoRA

**IMPORTANT:** The LoRA file needs to be downloaded manually from Civitai.

### Download Instructions:

1. **Visit the model page:**
   https://civitai.com/models/80799/playing-cards-or-concept-lora

2. **Click the "Download" button**
   - You may need to create a free Civitai account
   - Download the latest `.safetensors` file

3. **Save the file as:**
   ```bash
   /mnt/speedy/imagineer/models/lora/playing_cards_v1.safetensors
   ```

### Using wget/curl (if you have API access):

```bash
cd /mnt/speedy/imagineer/models/lora

# Option 1: If you have the direct download URL from Civitai
curl -L -o playing_cards_v1.safetensors "YOUR_DOWNLOAD_URL_HERE"

# Option 2: Using Civitai API (requires API key)
# Get your API key from https://civitai.com/user/account
curl -L -H "Authorization: Bearer YOUR_API_KEY" \\
  -o playing_cards_v1.safetensors \\
  "https://civitai.com/api/download/models/XXXXX"
```

## 🧪 Testing

Once the LoRA is downloaded, test it with a single card:

```bash
source venv/bin/activate

python examples/generate.py \\
  --prompt "PlayingCards. Ace of Spades. Large single black spade symbol centered in card, letter A in top-left and bottom-right corners. traditional playing card design" \\
  --lora-path /mnt/speedy/imagineer/models/lora/playing_cards_v1.safetensors \\
  --lora-weight 0.5 \\
  --width 512 \\
  --height 720 \\
  --steps 30
```

## 📋 Configuration Details

**Current Settings (`/mnt/speedy/imagineer/sets/config.yaml`):**

```yaml
card_deck:
  lora:
    path: "/mnt/speedy/imagineer/models/lora/playing_cards_v1.safetensors"
    weight: 0.5
```

**Trigger Word:** `PlayingCards` (already added to base_prompt)

**Recommended Weight Range:** 0.3 - 1.0 (default: 0.5)

## 🎯 What to Expect

### With LoRA:
- Better understanding of playing card structure
- More consistent suit symbols
- Proper corner value placement
- Traditional card styling

### Limitations:
- May still struggle with exact pip counts
- Face cards will need artistic interpretation
- The LoRA is trained on general playing card style, not specific deck designs

## 🚀 Next Steps (Phase 2):

After testing Option A, we can move to Option B - Training a Custom LoRA:

1. **Create Training Dataset**
   - Generate/source 50-100 card images
   - Write captions for each card
   - Organize in training format

2. **Train Custom LoRA**
   - Use existing `examples/train_lora.py`
   - Fine-tune on your specific card designs
   - Achieve perfect accuracy for all 54 cards

## 📝 Notes

- LoRA file size: ~36 MB
- Compatible with: Stable Diffusion 1.5 (what you're using)
- The server will automatically use the LoRA when generating card_deck batches
- If LoRA file is missing, generation will continue without it (with a warning)
