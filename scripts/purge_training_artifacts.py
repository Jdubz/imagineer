#!/usr/bin/env python3
"""
Utility script to invoke the training data retention cleanup.

This allows operators or scheduled jobs to trigger the purge logic on demand,
optionally running a dry-run to inspect what would be deleted.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, Optional

from server.tasks.training import purge_stale_training_artifacts


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Purge stale LoRA training datasets and logs.")
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help="Override retention window in days (default uses TRAINING_RETENTION_DAYS).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scan and report what would be removed without deleting anything.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the result as JSON for scripting/automation scenarios.",
    )
    return parser


def format_result(result: Dict[str, Any]) -> str:
    status = result.get("status", "success")
    days = result.get("retention_days")
    if status == "dry_run":
        runs = result.get("runs_matched", 0)
        datasets = result.get("datasets_marked", 0)
        logs = result.get("logs_marked", 0)
        return (
            f"[dry-run] Matching runs: {runs}, datasets marked: {datasets}, "
            f"logs marked: {logs} (retention window: {days} days)"
        )

    if status == "skipped":
        reason = result.get("reason", "retention-disabled")
        return f"Skipped training retention purge (reason: {reason})."

    datasets_removed = result.get("datasets_removed", 0)
    logs_removed = result.get("logs_removed", 0)
    runs_updated = result.get("runs_updated", 0)
    return (
        f"Removed {datasets_removed} datasets and {logs_removed} logs "
        f"across {runs_updated} runs (retention window: {days} days)."
    )


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    result = purge_stale_training_artifacts(retention_days=args.days, dry_run=args.dry_run)

    if args.json:
        json.dump(result, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        print(format_result(result))

    return 0 if result.get("status") in {"success", "dry_run", "skipped"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
