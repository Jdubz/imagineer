from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from server.legacy_import.collectors import collect_legacy_outputs


def _write_image(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"fake-image-bytes")
    metadata = path.with_suffix(".json")
    metadata.write_text(
        '{"prompt": "Test prompt", "created_at": "2025-01-15T12:34:56Z"}',
        encoding="utf-8",
    )


def test_collect_outputs_groups_assets(tmp_path: Path) -> None:
    outputs = tmp_path / "outputs"
    outputs.mkdir()

    single_image = outputs / "20250115_123456_sample.png"
    _write_image(single_image)

    deck_image = outputs / "card_deck_20251013_213519" / "20251013_213529_Two_of_Spades.png"
    _write_image(deck_image)

    lora_image = outputs / "lora_tests" / "ace.png"
    _write_image(lora_image)

    records = collect_legacy_outputs(outputs)
    assert len(records) == 3

    singles_record = next(rec for rec in records if rec.destination_path.parts[0] == "singles")
    assert singles_record.album.slug == "legacy-singles-2025-01"
    assert singles_record.destination_path == Path("singles/2025-01/20250115_123456_sample.png")
    assert singles_record.created_at == datetime(2025, 1, 15, 12, 34, 56, tzinfo=timezone.utc)

    deck_record = next(rec for rec in records if rec.album.album_type == "deck")
    assert deck_record.album.slug == "card_deck_20251013_213519"
    assert deck_record.destination_path == Path(
        "decks/card_deck_20251013_213519/20251013_213529_Two_of_Spades.png"
    )
    assert "Test prompt" in deck_record.tags

    lora_record = next(rec for rec in records if rec.album.album_type == "lora-experiment")
    assert lora_record.album.slug == "lora-tests"
    assert lora_record.destination_path == Path("lora-experiments/lora-tests/ace.png")
    assert lora_record.album.is_training_source
