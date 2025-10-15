# Set Data Directory

This directory is a placeholder. **The actual set data is stored externally.**

## External Set Location

```
/mnt/speedy/imagineer/sets/
├── config.yaml          # Set configurations (prompts, LoRAs, dimensions)
├── card_deck.csv        # 54 playing cards with visual layouts
├── tarot_deck.csv       # 22 Major Arcana
└── zodiac.csv           # 12 zodiac signs
```

## Configuration

The location is configured in `/home/jdubz/Development/imagineer/config.yaml`:

```yaml
sets:
  directory: "/mnt/speedy/imagineer/sets"
```

## Why External Storage?

Set data is stored on the fast external drive (`/mnt/speedy/`) because:
1. **Size** - CSV files and configurations are shared with model files and outputs
2. **Performance** - Fast SSD access for batch generation
3. **Organization** - Keeps all generation-related data in one location
4. **Flexibility** - Easy to edit without affecting the code repository

## Creating New Sets

1. Create a new CSV file in `/mnt/speedy/imagineer/sets/`
2. Add configuration in `/mnt/speedy/imagineer/sets/config.yaml`
3. The API will automatically discover and load it

See `docs/ARCHITECTURE.md` for detailed set configuration documentation.
