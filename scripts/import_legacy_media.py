#!/usr/bin/env python3
"""
Legacy Media Import Helper

This utility collects historical assets from the Imagineer outputs directory,
stages them under `data/legacy/`, and writes a manifest file describing the
assets. A future step will read the manifest to insert records into the
database.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from flask import Flask  # noqa: E402

from server.database import db  # noqa: E402
from server.legacy_import import collect_legacy_outputs  # noqa: E402
from server.legacy_import.importer import import_records  # noqa: E402
from server.legacy_import.stager import stage_records, write_manifest, write_summary  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage legacy Imagineer assets.")
    parser.add_argument(
        "--outputs-root",
        type=Path,
        default=Path("/mnt/speedy/imagineer/outputs"),
        help="Location of the legacy outputs directory.",
    )
    parser.add_argument(
        "--staging-root",
        type=Path,
        default=Path("data/legacy"),
        help="Directory where staged assets (and manifest) will be written.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="Manifest path. Defaults to <staging-root>/manifest.yaml",
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=None,
        help="Optional JSON file summarising the staging results.",
    )
    parser.add_argument(
        "--no-symlink",
        action="store_true",
        help="Copy files instead of creating symlinks inside data/legacy.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Collect and report, but do not copy/symlink any files.",
    )
    parser.add_argument(
        "--ingest",
        action="store_true",
        help="Insert staged assets into the Imagineer database after staging.",
    )
    parser.add_argument(
        "--verbose", "-v", action="count", default=0, help="Increase logging verbosity."
    )
    return parser.parse_args()


def configure_logging(verbosity: int) -> None:
    level = logging.WARNING
    if verbosity == 1:
        level = logging.INFO
    elif verbosity >= 2:
        level = logging.DEBUG
    logging.basicConfig(level=level, format="%(levelname)s %(message)s")


def create_app() -> Flask:
    app = Flask(__name__)
    db_path = REPO_ROOT / "instance" / "imagineer.db"
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
    return app


def main() -> int:
    args = parse_args()
    configure_logging(args.verbose)

    records = collect_legacy_outputs(args.outputs_root)

    print("LEGACY MEDIA IMPORT")
    print("===================")
    print(f"Outputs directory: {args.outputs_root}")
    print(f"Discovered images: {len(records)}")

    counter = Counter(record.album.slug for record in records)
    for slug, count in sorted(counter.items()):
        print(f"  - {slug}: {count} assets")

    staging_root = args.staging_root
    manifest_path = args.manifest or staging_root / "manifest.yaml"
    summary_path = args.summary or staging_root / "staging-summary.json"

    if args.dry_run:
        print("\nDry-run mode enabled. No files were staged.")
        write_manifest(records, manifest_path)
        print(f"Manifest written to {manifest_path}")
        if args.ingest:
            print("⚠️  --ingest ignored during dry-run.")
        return 0

    summary = stage_records(
        records,
        staging_root,
        copy_metadata=True,
        use_symlinks=not args.no_symlink,
    )

    write_manifest(records, manifest_path)
    write_summary(summary, summary_path)

    print("\nStaging complete:")
    print(json.dumps(summary.__dict__, indent=2))
    print(f"Manifest: {manifest_path}")
    print(f"Summary:  {summary_path}")

    if args.ingest:
        app = create_app()
        with app.app_context():
            stats = import_records(records, staging_root)
        print("\nDatabase import complete:")
        print(json.dumps(stats.__dict__, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
