# Bug Remediation Agent Docker Optimizations

The bug-remediation worker currently runs inside `ghcr.io/jdubz/imagineer/bug-cli:latest`
(built from `docker/claude-cli/Dockerfile`).  The last dry run exposed several
missing tools and dependency gaps that make automation brittle.  This note
collects concrete Dockerfile tweaks so that test runs succeed without manual
bootstrap work.

## 1. Ensure required system utilities are present

| Problem observed | Suggested fix |
| ---------------- | ------------- |
| `Error: spawn ps ENOENT` when Claude tries to enumerate child processes (container lacks `ps`). | Add `procps` (or at minimum `procps-ng`) to the `apt-get install` list so the standard `ps` binary is available. |
| Git pre-commit hook errors if `bash` subshells try to inspect processes. | Covered by the same `procps` addition; no further change needed once `ps` exists. |
| Git push fails with HTTPS prompts | Mount `~/.git-credentials` into `/home/node/.git-credentials` and configure `credential.helper store` so the agent reuses your local token. |

```dockerfile
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    curl \
    ca-certificates \
    openssh-client \
    rsync \
    jq \
    procps \   # ← new
 && rm -rf /var/lib/apt/lists/*
```

## 2. Pre-install Python dependencies globally

| Problem observed | Suggested fix |
| ---------------- | ------------- |
| `ModuleNotFoundError: No module named 'yaml'` when running `scripts/test_trigger_words.py`. | Install `pyyaml` globally (either via `apt-get install python3-yaml` or `pip install pyyaml`).  Keeping it in the image avoids every run from failing before tests finish. |
| Pre-commit hook attempts to `source venv/bin/activate`, but remediation containers deliberately skip virtualenvs. | Installing dependencies system-wide keeps the hook harmless—ensure the hook doesn’t require activation, or drop a stub `venv/bin/activate` script if needed. |

```dockerfile
RUN pip3 install --no-cache-dir --break-system-packages \
    black==24.10.0 \
    flake8==7.1.1 \
    pytest==8.3.4 \
    pytest-cov==6.0.0 \
    isort==5.13.2 \
    pyyaml==6.0.2   # ← new
```

If tighter control of system packages is preferred, swap the `pip` line for:

```dockerfile
RUN apt-get update && apt-get install -y python3-yaml && rm -rf /var/lib/apt/lists/*
```

> **Note:** We do not need virtualenv isolation inside the worker image—installing packages globally keeps the filesystem simpler and avoids per-run environment creation costs.

## 3. Avoid Rollup native binary fetch failures

`npm test` uses Vite/Vitest, which relies on Rollup.  The remediation bootstrap
runs `npm install --omit=optional`, which skips Rollup’s platform-specific
package (`@rollup/rollup-linux-x64-gnu`).  Vitest then crashes because the
native binary is absent.  There are two viable mitigations:

The updated image now pre-installs the native binary so Vitest works even when
optional packages are skipped later:

```dockerfile
RUN mkdir -p /opt/imagineer/node_modules && \
    npm install --prefix /opt/imagineer @rollup/rollup-linux-x64-gnu@latest && \
    chown -R node:node /opt/imagineer
```

If this cache ever causes version drift, the simpler fallback is to drop
`--omit=optional` from `scripts/bug_reports/agent_bootstrap.sh`; expect slightly
longer install times if you choose that route.

## 4. Cache-friendly improvements (optional)

- **Pre-create `/opt/imagineer/node_modules`** and seed it with the project’s prod dependencies by running `npm ci --omit=dev` during image build.  The bootstrap already rsyncs from `IMAGINEER_NODE_MODULES_CACHE`; filling it during build means typical verification runs only add dev/test packages.
- **Install `pnpm` or `corepack enable`** if we later switch to deterministic package managers; doing it in the image avoids per-run downloads.

These adjustments reduce cold-start time and eliminate the recurring failures observed during the latest remediation attempt.  Apply them to the Dockerfile, rebuild the image locally (no registry push required for the on-prem runner), and restart the agent before re-queuing automated bug fixes.***
