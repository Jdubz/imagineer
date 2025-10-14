#!/bin/bash
# Dynamically test all LoRAs in the lora directory
# Generates one Ace of Spades for each LoRA

LORA_DIR="/mnt/speedy/imagineer/models/lora"
OUTPUT_DIR="/mnt/speedy/imagineer/outputs/lora_tests"
mkdir -p "$OUTPUT_DIR"

# Activate venv
source venv/bin/activate

# Test prompt for Ace of Spades
PROMPT="PlayingCards. Ace of Spades. Large single black spade symbol centered in card, letter A in top-left and bottom-right corners. traditional playing card design"

echo "Testing all LoRAs for playing card generation..."
echo "========================================="
echo ""

# Counter for successful/failed generations
success_count=0
fail_count=0
skip_count=0

# Find all .safetensors files in the lora directory
while IFS= read -r -d '' lora_path; do
    # Get just the filename
    lora_filename=$(basename "$lora_path")

    # Skip README
    if [[ "$lora_filename" == "README.md" ]]; then
        continue
    fi

    echo "Testing: $lora_filename"

    # Get file size to provide info
    size=$(stat -c%s "$lora_path")
    size_mb=$((size / 1024 / 1024))
    echo "  Size: ${size_mb}MB"

    # Warn if file is very large (likely SDXL)
    if [ $size_mb -gt 150 ]; then
        echo "  ⚠ Warning: Large file, might be SDXL (incompatible with SD 1.5)"
    fi

    # Clean filename for output (remove extension)
    clean_name="${lora_filename%.*}"
    output_path="$OUTPUT_DIR/${clean_name}.png"
    log_path="$OUTPUT_DIR/${clean_name}.log"

    echo "  Output: $output_path"
    echo "  Generating..."

    # Try to generate with this LoRA
    if timeout 300 python examples/generate.py \
        --prompt "$PROMPT" \
        --lora-path "$lora_path" \
        --lora-weight 0.6 \
        --width 512 \
        --height 720 \
        --steps 25 \
        --seed 42 \
        --output "$output_path" > "$log_path" 2>&1; then

        echo "  ✓ SUCCESS"
        success_count=$((success_count + 1))
    else
        echo "  ✗ FAILED (see $log_path for details)"
        fail_count=$((fail_count + 1))
    fi

    echo ""

done < <(find "$LORA_DIR" -maxdepth 1 -name "*.safetensors" -print0 | sort -z)

echo "========================================="
echo "Testing complete!"
echo ""
echo "Results:"
echo "  ✓ Successful: $success_count"
echo "  ✗ Failed: $fail_count"
echo ""
echo "Output directory: $OUTPUT_DIR"
echo ""
echo "To view successful generations:"
echo "  ls -lh $OUTPUT_DIR/*.png"
