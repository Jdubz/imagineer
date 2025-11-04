#!/usr/bin/env python
"""
Bug report maintenance CLI for the database-backed workflow.

Allows operators to list, inspect, update, delete, and purge bug reports
stored in the Imagineer database.
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

from server.api import app as flask_app  # noqa: E402
from server.config_loader import load_config  # noqa: E402
from server.services import bug_reports as bug_report_service  # noqa: E402


def _format_timestamp(value: Optional[str]) -> str:
    return value or "-"


def _with_context(func, *args, **kwargs):
    with flask_app.app_context():
        return func(*args, **kwargs)


def cmd_list(args: argparse.Namespace) -> int:
    status = args.status
    limit = args.limit or 100

    records, total = _with_context(
        bug_report_service.list_bug_reports,
        status=status,
        page=1,
        per_page=limit,
    )

    if args.json:
        payload = [record.to_dict(include_context=args.include_context) for record in records]
        print(json.dumps({"total": total, "reports": payload}, indent=2))
        return 0

    if not records:
        print("No bug reports found.")
        return 0

    header = (
        f"{'Report ID':<36} {'Status':<14} {'Submitted At':<25} "
        f"{'Submitted By':<30} {'Trace ID':<32} {'Logs':<5} {'Net':<5}"
    )
    print(header)
    print("-" * len(header))

    for record in records:
        data = record.to_dict(include_context=False)
        submitted_at = _format_timestamp(data.get("submitted_at"))
        submitted_by = (data.get("submitted_by") or "-")[:29]
        trace_id = (data.get("trace_id") or "-")[:31]
        has_logs = "Y" if data.get("has_recent_logs") else "-"
        has_network = "Y" if data.get("has_network_events") else "-"
        print(
            f"{record.report_id:<36} {data.get('status', '-'):<14} "
            f"{submitted_at:<25} {submitted_by:<30} {trace_id:<32} "
            f"{has_logs:<5} {has_network:<5}"
        )

    return 0


def cmd_show(args: argparse.Namespace) -> int:
    record = _with_context(bug_report_service.get_bug_report, args.report_id)
    if not record:
        print(f"Report {args.report_id} not found.", file=sys.stderr)
        return 1

    payload = record.to_dict(include_context=True)
    print(json.dumps(payload, indent=2))
    return 0


def cmd_update(args: argparse.Namespace) -> int:
    resolution_payload = json.loads(args.resolution) if args.resolution else None
    record = _with_context(
        bug_report_service.update_bug_report_status,
        report_id=args.report_id,
        status=args.status,
        actor_id=args.actor,
        resolution_notes=(resolution_payload or {}).get("notes") if resolution_payload else None,
        resolution_commit_sha=(
            (resolution_payload or {}).get("commit_sha") if resolution_payload else None
        ),
    )

    if not record:
        print(f"Report {args.report_id} not found.", file=sys.stderr)
        return 1

    print(json.dumps(record.to_dict(include_context=False), indent=2))
    return 0


def cmd_delete(args: argparse.Namespace) -> int:
    deleted = _with_context(bug_report_service.delete_bug_report, args.report_id)
    if not deleted:
        print(f"Report {args.report_id} not found.", file=sys.stderr)
        return 1

    print(f"Deleted report {args.report_id}.")
    return 0


def cmd_purge(args: argparse.Namespace) -> int:
    config = load_config()
    default_days = int(config.get("bug_reports", {}).get("retention_days", 30))
    days = args.days or default_days
    if days <= 0:
        print("Retention disabled (days <= 0).", file=sys.stderr)
        return 1

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    results = _with_context(
        bug_report_service.purge_bug_reports,
        cutoff=cutoff,
        dry_run=args.dry_run,
    )
    results["cutoff"] = cutoff.isoformat().replace("+00:00", "Z")
    status = "dry_run" if args.dry_run else "success"
    print(json.dumps({"status": status, "results": results}, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bug report maintenance CLI (database-backed).")

    subparsers = parser.add_subparsers(required=True, dest="command")

    list_parser = subparsers.add_parser("list", help="List stored bug reports")
    list_parser.add_argument(
        "--status", choices=["open", "in_progress", "resolved"], help="Filter by status"
    )
    list_parser.add_argument(
        "--limit", type=int, help="Maximum number of reports to list (default 100)"
    )
    list_parser.add_argument("--json", action="store_true", help="Emit JSON output")
    list_parser.add_argument(
        "--include-context",
        action="store_true",
        help="Include full context (logs/network) when using --json",
    )
    list_parser.set_defaults(func=cmd_list)

    show_parser = subparsers.add_parser("show", help="Show full bug report payload")
    show_parser.add_argument("report_id", help="Report identifier")
    show_parser.set_defaults(func=cmd_show)

    update_parser = subparsers.add_parser("update", help="Update bug report status/resolution")
    update_parser.add_argument("report_id")
    update_parser.add_argument(
        "--status", choices=["open", "in_progress", "resolved"], help="New status"
    )
    update_parser.add_argument(
        "--resolution",
        help='Resolution metadata as JSON (e.g. \'{"notes": "Fixed", "commit_sha": "..."}\')',
    )
    update_parser.add_argument("--actor", help="Actor identifier performing the update")
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
