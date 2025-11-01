# Bug Report Auto-Fix Pipeline Plan

## Objective
- Automate follow-up fixes for validated bug reports by running a Claude CLI container that applies code changes, commits them, and pushes directly to the `develop` branch.
- Keep the existing bug-report triage flow intact while adding an optional “auto-fix” stage that operates only after required metadata (repro steps, priority, component tags) is provided.

## Constraints & Assumptions
- Claude CLI runs inside the maintained Docker image (`anthropic/claude-coder`), already used elsewhere in this repo.
- Git operations must happen on a temporary workspace inside the container; we never mutate the host checkout directly.
- Auto-fix is allowed only for repositories with the automation service account’s write access and when the bug severity ≤ “High” (critical issues still require human review).
- The pipeline runs under GitHub Actions; secrets (`GH_TOKEN_AUTOFIX`, `CLAUDE_API_KEY`) are available there.
- We must respect branch protections on `main`; therefore, all automation targets `develop`.
- Bug report payloads arrive through the existing issue template + triage script located at `scripts/bug_reports`.

## High-Level Flow
1. **Trigger**: Bug report issue is labeled `auto-fix` (manual gate by triage or confidence score ≥ threshold).
2. **GitHub Action**: New workflow `bug-report-autofix.yml` runs on label event.
3. **Container Setup**: Use Docker-in-Docker step to launch Claude CLI container with repo volume mounted.
4. **Repo Prep**:
   - Clone fresh copy of `git@github.com:Jdubz/imagineer.git`.
   - Checkout `origin/develop`.
   - Copy project dotfiles/configs required by Claude from host workspace (e.g., `.claude.json`, `.codex`, `.env.example`).
5. **Context Building**:
   - Export bug issue metadata into `/tmp/autofix/context.md`.
   - Include failing tests/repro info if provided (pulled from issue body or attachments).
6. **Claude Invocation**:
   - Run: `claude codex plan --prompt context.md --output plan.json`.
   - Approve plan automatically if it sets `risk <= medium`; otherwise abort with comment on issue.
   - Execute: `claude codex apply plan.json`.
7. **Validation**:
   - Run targeted tests using `make test-backend` / `npm test` depending on affected components (deduced from labels).
   - Ensure `git status` is clean except for intended changes.
8. **Commit & Push**:
   - Configure committer `Imagineer AutoFix Bot <infra+autofix@joshwentworth.com>`.
   - Commit message template: `fix: <short summary> (auto-fix)`.
   - Push to `origin develop`.
9. **Issue Updates**:
   - Comment with patch summary, test results, and commit SHA.
   - Remove `auto-fix` label, add `autofix-pushed`.

## Detailed Tasks
1. **Workflow Definition**
   - Create `.github/workflows/bug-report-autofix.yml`.
   - Trigger: `issues`, activity type `labeled`.
   - Conditions: issue label equals `auto-fix`, issue state is `open`, actor is bot service account or triage team.
   - Jobs:
     - `prep`: gather issue details, write JSON artifact.
     - `autofix`: run inside `ubuntu-latest`, set up Docker, launch Claude container.
2. **Claude Container Invocation**
   - Image: `ghcr.io/anthropic/claude-coder:latest`.
   - Mount `/workspace`.
   - Inject config files + `.gitconfig` with safe defaults.
   - Pass environment variables: `CLAUDE_API_KEY`, `AUTOFIX_COMMITTER_NAME`, `AUTOFIX_COMMITTER_EMAIL`.
   - Provide bug context via `--prompt`.
3. **Repo Sync Script**
   - New script `scripts/autofix/run_autofix.sh` executed inside container.
   - Responsibilities:
     - Clone repo → checkout develop → fetch latest.
     - Copy config templates (list maintained in `scripts/autofix/config_manifest.txt`).
     - Call Claude CLI (`claude codex plan/apply`).
     - Run component-specific tests (detected via bug labels).
     - Commit + push.
     - Emit short summary JSON for GitHub comment.
4. **Tests Mapping Table**
   - Maintain map in `scripts/autofix/test_matrix.json`:
     - `frontend` → `npm test -- --run`.
     - `backend` → `pytest tests/backend`.
     - `infra` → `terraform validate`.
     - Fallback → `make test`.
5. **Secrets & Permissions**
   - Add `GH_TOKEN_AUTOFIX` with repo `contents: write`.
   - Reuse `CLAUDE_API_KEY`.
   - Configure GitHub Action to use bot SSH deploy key (read/write).
6. **Issue Commenter**
   - New helper script `scripts/autofix/comment_issue.py` posts status updates via GitHub REST (use `GH_TOKEN_AUTOFIX`).
   - Comment includes:
     - ✅/⚠️ result emoji.
     - Tests run + durations.
     - Commit SHA + link.
     - Reminder for human review (optional).
7. **Failure Handling**
   - If plan generation fails or tests fail:
     - Abort pipeline.
     - Comment on issue with failure reason and attach logs.
     - Leave `auto-fix` label for manual follow-up.
   - If git push fails (branch protection, diverged history):
     - Fetch latest develop, rebase, retry once.
     - On second failure, abort and comment.
8. **Logging & Artifact Storage**
   - Upload Claude plan (`plan.json`), diff patch, test logs as workflow artifacts for audit.
   - Optional: store in `logs/autofix` bucket (future enhancement).
9. **Observability**
   - Extend `docs/deployment/DEPLOYMENT_STATUS_AND_NEXT_STEPS.md` with checklist.
   - Add metrics hook (future): push success/failure stats to `logs/autofix_summary.csv`.

## Rollout Plan
1. Implement workflow + scripts behind feature flag (`ENABLE_AUTOFIX` repo secret).
2. Dry run on staging repo (`imagineer-autofix-playground`).
3. Enable for real repo with limited bug labels (`component:frontend`, `component:backend`).
4. Monitor first 5 auto-fix commits manually.
5. Iterate on test matrix and Claude prompt templates based on outcomes.

## Risks & Mitigations
- **Risk:** Automated fix introduces regression.
  - *Mitigation:* Restrict to low/medium priority bugs, enforce test suite per component, require follow-up review even after push.
- **Risk:** Claude CLI modifies unintended files.
  - *Mitigation:* Post-plan check ensures changed paths match bug scope; abort otherwise.
- **Risk:** Push conflicts with human work.
  - *Mitigation:* Use `git pull --rebase` before push; if conflicts appear, notify via issue comment rather than auto-resolving.
- **Risk:** Secrets leakage.
  - *Mitigation:* Run in ephemeral GitHub Actions runners; mount configs read-only; scrub logs.

## Next Actions
1. Author `.github/workflows/bug-report-autofix.yml` per above.
2. Build `scripts/autofix/run_autofix.sh`, `config_manifest.txt`, `test_matrix.json`, `comment_issue.py`.
3. Update documentation (`docs/guides/AUTOFIX.md`).
4. Create service account + token rotation procedure.
5. Pilot with staged bug report and validate end-to-end.
