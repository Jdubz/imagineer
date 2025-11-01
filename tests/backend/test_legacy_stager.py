from __future__ import annotations

from pathlib import Path

from server.legacy_import.models import LegacyAlbum, LegacyImageRecord
from server.legacy_import.stager import StageSummary, stage_records


def make_record(tmp_path: Path) -> LegacyImageRecord:
    source = tmp_path / "source.png"
    source.write_bytes(b"image-bytes")
    metadata = source.with_suffix(".json")
    metadata.write_text('{"prompt": "stage me"}', encoding="utf-8")

    album = LegacyAlbum(
        slug="legacy-singles-2025-01", name="Legacy Singles 2025-01", album_type="singles"
    )
    return LegacyImageRecord(
        source_path=source,
        metadata_path=metadata,
        destination_path=Path("singles/2025-01/source.png"),
        album=album,
        created_at=None,
        metadata={"prompt": "stage me"},
    )


def test_stage_records_symlink(tmp_path: Path) -> None:
    record = make_record(tmp_path)
    staging_root = tmp_path / "staging"

    summary = stage_records([record], staging_root, use_symlinks=True)
    assert summary == StageSummary(copied=1, skipped=0, metadata_copied=1)

    dest_image = staging_root / record.destination_path
    assert dest_image.is_symlink()
    assert dest_image.resolve() == record.source_path

    dest_metadata = dest_image.with_suffix(".json")
    assert dest_metadata.exists()
    assert dest_metadata.read_text(encoding="utf-8") == '{"prompt": "stage me"}'


def test_stage_records_copy(tmp_path: Path) -> None:
    record = make_record(tmp_path)
    staging_root = tmp_path / "staging"

    summary = stage_records([record], staging_root, use_symlinks=False)
    assert summary.copied == 1
    dest_image = staging_root / record.destination_path
    assert dest_image.is_file()
    assert dest_image.read_bytes() == b"image-bytes"
