#!/usr/bin/env python3
"""
Utility script to comment on or update labels for a GitHub issue.

Usage examples:

  python scripts/autofix/comment_issue.py --repo Jdubz/imagineer \
      --issue-number 123 --comment-file /tmp/comment.md

  python scripts/autofix/comment_issue.py --repo Jdubz/imagineer \
      --issue-number 123 --add-labels autofix-pushed --remove-labels auto-fix
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Iterable, Optional


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="GitHub issue comment/label helper.")
    parser.add_argument("--repo", required=True, help="Repository in owner/name format.")
    parser.add_argument("--issue-number", type=int, required=True, help="Issue number.")
    parser.add_argument(
        "--token",
        default=os.environ.get("GH_TOKEN_AUTOFIX") or os.environ.get("GITHUB_TOKEN"),
        help="GitHub token (falls back to GH_TOKEN_AUTOFIX/GITHUB_TOKEN).",
    )
    parser.add_argument("--comment", help="Comment body.")
    parser.add_argument("--comment-file", help="Path to comment body file.")
    parser.add_argument(
        "--add-labels",
        nargs="*",
        default=[],
        help="Labels to add to the issue.",
    )
    parser.add_argument(
        "--remove-labels",
        nargs="*",
        default=[],
        help="Labels to remove from the issue.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print actions without performing API calls.",
    )
    return parser.parse_args()


def github_request(
    method: str, url: str, token: str | None, payload: Optional[dict] = None
) -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Imagineer-Autofix-Bot",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            if response.status >= 300 or response.status < 200:
                raise RuntimeError(f"GitHub API call failed with status {response.status}")
            body = response.read()
            if not body:
                return {}
            return json.loads(body.decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        raise RuntimeError(f"GitHub API error {exc.code}: {body}") from exc


def comment_issue(args: argparse.Namespace, body: str) -> None:
    url = f"https://api.github.com/repos/{args.repo}/issues/{args.issue_number}/comments"
    if args.dry_run:
        print(f"[dry-run] POST {url}\n{body}")
        return
    github_request("POST", url, args.token, {"body": body})


def add_labels(args: argparse.Namespace, labels: Iterable[str]) -> None:
    labels = [label for label in labels if label]
    if not labels:
        return
    url = f"https://api.github.com/repos/{args.repo}/issues/{args.issue_number}/labels"
    if args.dry_run:
        print(f"[dry-run] POST {url} {labels}")
        return
    github_request("POST", url, args.token, {"labels": labels})


def remove_labels(args: argparse.Namespace, labels: Iterable[str]) -> None:
    for label in labels:
        if not label:
            continue
        label_encoded = urllib.parse.quote(label)
        base_url = f"https://api.github.com/repos/{args.repo}/issues/{args.issue_number}"
        url = f"{base_url}/labels/{label_encoded}"
        if args.dry_run:
            print(f"[dry-run] DELETE {url}")
            continue
        github_request("DELETE", url, args.token)


def main() -> int:
    args = parse_args()
    if not args.token and not args.dry_run:
        print("Error: GitHub token not provided.", file=sys.stderr)
        return 1

    comment_body = None
    if args.comment_file:
        try:
            with open(args.comment_file, "r", encoding="utf-8") as handle:
                comment_body = handle.read()
        except FileNotFoundError:
            print(f"Error: comment file not found: {args.comment_file}", file=sys.stderr)
            return 1
    elif args.comment:
        comment_body = args.comment

    if comment_body:
        comment_issue(args, comment_body)

    if args.add_labels:
        add_labels(args, args.add_labels)

    if args.remove_labels:
        remove_labels(args, args.remove_labels)

    if not any([comment_body, args.add_labels, args.remove_labels]):
        msg = (
            "No action requested; specify --comment, --comment-file, "
            "--add-labels, or --remove-labels."
        )
        print(msg, file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
