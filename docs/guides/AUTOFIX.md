# Imagineer Bug Report Auto-Fix Pipeline

_Last updated: 2025-11-01_

This guide explains how the automated bug report remediation pipeline works, how to
operate it safely, and how to triage outputs.

## Overview

When a triaged bug report is labelled `auto-fix`, GitHub Actions launches the
Claude-powered auto-fix pipeline. The workflow:

1. Collects issue metadata and builds a context prompt.
2. Spins up the Claude CLI container inside GitHub Actions.
3. Clones `develop`, synchronises required config files, and asks Claude to draft a plan.
4. Applies the plan, runs targeted tests, commits, and pushes directly to `develop`.
5. Comments on the originating issue with summary + test results and adjusts labels.

Use this automation only for low/medium risk bugs with clear repro steps. Critical or
ambiguous failures still require manual intervention.

## Triggering the Pipeline

- Ensure the GitHub issue contains:
  - Reproduction steps.
  - Component label (e.g. `frontend`, `backend`, `training`).
  - Optional severity (must be `low`, `medium`, or `high` — `critical` blocks automation).
- Apply the `auto-fix` label. The workflow ignores closed issues and anything without
  sufficient metadata.

## Workflow Files

- `.github/workflows/bug-report-autofix.yml`: entry point invoked on `issues:labeled`.
- `scripts/autofix/run_autofix.sh`: runs inside the Claude container to clone, apply
  fixes, run tests, and push commits.
- `scripts/autofix/config_manifest.txt`: list of config files copied into the
  container workspace before invoking Claude.
- `scripts/autofix/test_matrix.json`: maps component labels to test commands.
- `scripts/autofix/comment_issue.py`: helper for posting status updates and adjusting labels.

## Environment & Secrets

The workflow expects the following GitHub secrets:

- `GH_TOKEN_AUTOFIX`: PAT with `contents:write`, `issues:write`.
- `CLAUDE_API_KEY`: API token for Claude CLI.
- `AUTOFIX_DEPLOY_KEY`: SSH private key with push access (optional; otherwise use PAT).
- `CLAUDE_CREDENTIALS_JSON`: The contents of `~/.claude/.credentials.json` (copied into the container).
- `GH_HOSTS_YML`: The contents of `~/.config/gh/hosts.yml` for authenticated `gh` usage.

If you run the workflow on self-hosted runners, you may omit the last two secrets
and instead place the files at `~/.claude/.credentials.json` and
`~/.config/gh/hosts.yml` on the runner; they will be mounted automatically.

Optional repository or environment secrets:

- `ENABLE_AUTOFIX`: set to `true` to activate the final push step. Absent or `false`
  keeps the pipeline in dry-run mode.

## Test Mapping

`scripts/autofix/test_matrix.json` maps labels to specific verification commands.
If multiple labels are present, the first match wins; fallback is `make test`.

| Label     | Command                         |
|-----------|---------------------------------|
| frontend  | `npm test -- --runInBand`       |
| backend   | `pytest tests/backend`          |
| training  | `pytest tests/backend/test_phase5_training.py` |
| infra     | `terraform validate`            |
| docs      | `npm run lint:docs`             |
| default   | `make test`                     |

Adjust this matrix when new components are onboarded.

## Output & Issue Comment

On success the bot comment includes:

- ✅ emoji and message summary.
- Tests executed + status.
- Commit SHA with link.
- Reminder for human review.

On failure the comment includes a ⚠️ emoji, failure reason, and the workflow retains
the `auto-fix` label so humans can inspect logs.

Artifacts uploaded per run:

- Claude plan JSON (`plan.json`).
- Diff patch (`autofix.patch`).
- Test logs (`test.log`).
- Summary JSON (`summary.json`).

## Manual Overrides

- To cancel an ongoing run, remove the `auto-fix` label.
- If the workflow pushed an unsatisfactory commit, revert it manually and re-open the
  issue; automation will not attempt a second fix until `auto-fix` is re-applied.

## Roadmap

- Integrate risk scoring feedback loop from manually-reviewed runs.
- Emit success/failure metrics to observability stack.
- Extend `run_autofix.sh` to detect and respect code ownership boundaries.
