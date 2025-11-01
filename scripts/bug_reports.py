#!/usr/bin/env python
"""
Bug report maintenance CLI.

Provides helpers for listing, showing, updating, deleting, and purging stored
bug report JSON files. This mirrors the admin API so operators can run the
workflow from cron or local shells without spinning up a web session.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from server.bug_reports.storage import (  # noqa: E402
    BugReportStorageError,
    delete_report,
    list_reports,
    load_report,
    purge_reports_older_than,
    update_report,
)
from server.config_loader import load_config  # noqa: E402
from server.routes.bug_reports import get_bug_reports_dir  # noqa: E402


def _resolve_root(path: Optional[str]) -> Path:
    if path:
        return Path(path).expanduser()
    return Path(get_bug_reports_dir()).expanduser()


def cmd_list(args: argparse.Namespace) -> int:
    root = _resolve_root(args.root)
    summaries = list_reports(root, status=args.status)
    if args.json:
        print(json.dumps([summary.to_dict(root=root) for summary in summaries], indent=2))
        return 0

    if not summaries:
        print("No bug reports found.")
        return 0

    print(f"{'Report ID':<36} {'Status':<9} {'Submitted At':<25} {'Submitted By':<30} Size")
    print("-" * 110)
    for summary in summaries:
        submitted = summary.submitted_at_iso or "-"
        submitted_by = summary.submitted_by or "-"
        status = summary.status
        size = summary.size_bytes
        print(f"{summary.report_id:<36} {status:<9} " f"{submitted:<25} {submitted_by:<30} {size}")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    root = _resolve_root(args.root)
    try:
        report = load_report(args.report_id, root)
    except FileNotFoundError:
        print(f"Report {args.report_id} not found.", file=sys.stderr)
        return 1
    except BugReportStorageError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps(report, indent=2))
    return 0


def cmd_update(args: argparse.Namespace) -> int:
    root = _resolve_root(args.root)
    resolution = json.loads(args.resolution) if args.resolution else None
    try:
        report = update_report(
            args.report_id,
            root,
            status=args.status,
            resolution=resolution,
        )
    except FileNotFoundError:
        print(f"Report {args.report_id} not found.", file=sys.stderr)
        return 1
    except (ValueError, BugReportStorageError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps(report, indent=2))
    return 0


def cmd_delete(args: argparse.Namespace) -> int:
    root = _resolve_root(args.root)
    try:
        delete_report(args.report_id, root)
    except FileNotFoundError:
        print(f"Report {args.report_id} not found.", file=sys.stderr)
        return 1
    except BugReportStorageError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"Deleted report {args.report_id}.")
    return 0


def cmd_purge(args: argparse.Namespace) -> int:
    root = _resolve_root(args.root)
    config = load_config()
    default_days = int(config.get("bug_reports", {}).get("retention_days", 30))
    days = args.days or default_days
    if days <= 0:
        print("Retention disabled (days <= 0).", file=sys.stderr)
        return 1

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    if args.dry_run:
        summaries = list_reports(root)
        matching = [
            summary
            for summary in summaries
            if summary.submitted_at and summary.submitted_at < cutoff
        ]
        print(
            json.dumps(
                {
                    "status": "dry_run",
                    "cutoff": cutoff.isoformat().replace("+00:00", "Z"),
                    "matched": len(matching),
                    "reports": [summary.to_dict(root=root) for summary in matching],
                },
                indent=2,
            )
        )
        return 0

    results = purge_reports_older_than(root, cutoff)
    print(json.dumps({"status": "success", "results": results}, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bug report maintenance CLI.")
    parser.add_argument("--root", help="Override bug report storage directory")

    subparsers = parser.add_subparsers(required=True, dest="command")

    list_parser = subparsers.add_parser("list", help="List stored bug reports")
    list_parser.add_argument("--status", choices=["open", "resolved"], help="Filter by status")
    list_parser.add_argument("--json", action="store_true", help="Emit JSON output")
    list_parser.set_defaults(func=cmd_list)

    show_parser = subparsers.add_parser("show", help="Show full bug report payload")
    show_parser.add_argument("report_id", help="Report identifier")
    show_parser.set_defaults(func=cmd_show)

    update_parser = subparsers.add_parser("update", help="Update bug report status/resolution")
    update_parser.add_argument("report_id")
    update_parser.add_argument("--status", choices=["open", "resolved"], help="New status")
    update_parser.add_argument(
        "--resolution",
        help='Resolution metadata as JSON (e.g. \'{"commit": "abc123"}\')',
    )
    update_parser.set_defaults(func=cmd_update)

    delete_parser = subparsers.add_parser("delete", help="Delete a bug report")
    delete_parser.add_argument("report_id")
    delete_parser.set_defaults(func=cmd_delete)

    purge_parser = subparsers.add_parser("purge", help="Delete bug reports older than N days")
    purge_parser.add_argument(
        "--days", type=int, help="Retention window in days (defaults to config)"
    )
    purge_parser.add_argument("--dry-run", action="store_true", help="Preview without deleting")
    purge_parser.set_defaults(func=cmd_purge)

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
