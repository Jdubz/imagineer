# Bug Remediation Agent Quality Improvements

**Created:** November 4, 2025
**Status:** Proposal

## Problem Statement

Analysis of recent automated bug remediation attempts reveals two critical issues:

1. **Test Flakiness:** Tests must pass, but identical fixes fail/succeed non-deterministically
2. **Incomplete Fixes:** Agents make changes but don't verify they've actually fixed the UI problem

### Evidence

**Test Flakiness Example:**
- Bug `bug_20251104_012222_95ef59cc` required 5 identical attempts before tests passed
- Commits 0217b10 and 7445a1b have identical code changes
- Local test run just passed (275 tests) but agents see failures

**Incomplete Fix Example:**
- Bug `bug_20251104_010033_ad3420e9` (prevent navigation when clicking delete button)
- Manual fix b283869: Added `e.preventDefault()` to event handlers ✅ Correct
- Automated attempt d9f5db6: Only modified `package-lock.json` ❌ Wrong
- Agent didn't verify the button behavior was actually fixed

## Solution Architecture

### Part 1: Test Stability Improvements

#### 1.1 Test Retry Strategy

**Current State:**
```bash
# agent_bootstrap.sh:157
npm test -- --run  # Fails entire session on any flaky test
```

**Proposed:**
```bash
# Retry failed tests up to 3 times
npm test -- --run --retry=3
```

**Implementation:**
- Update `web/vitest.config.js` to add retry configuration
- Add `--retry=3` flag to test command in agent_bootstrap.sh
- Log retry attempts to help identify consistently flaky tests

```javascript
// web/vitest.config.js
export default defineConfig({
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    retry: 3, // Retry failed tests up to 3 times
    css: true,
    // ...
  },
})
```

**Benefits:**
- Prevents valid fixes from being rejected due to transient test failures
- Still maintains quality bar (tests must eventually pass)
- Exposes consistently flaky tests via logs

#### 1.2 Test Isolation & Cleanup

**Problem:** Shared state between tests can cause non-deterministic failures

**Solutions:**
1. Add global test teardown to clean DOM/localStorage/session storage
2. Use `vi.clearAllMocks()` in beforeEach blocks
3. Add test isolation checks to CI

```typescript
// web/src/test/setup.ts
import { afterEach, beforeEach } from 'vitest'
import '@testing-library/jest-dom'

beforeEach(() => {
  // Clear all mocks before each test
  vi.clearAllMocks()
})

afterEach(() => {
  // Clean up DOM after each test
  document.body.innerHTML = ''
  document.head.innerHTML = ''

  // Clear storage
  localStorage.clear()
  sessionStorage.clear()

  // Clear any timers
  vi.clearAllTimers()
})
```

#### 1.3 Flaky Test Detection

**Add to agent_bootstrap.sh:**
```bash
run_tests_with_flake_detection() {
  local max_retries=3
  local attempt=1
  local failed_tests=()

  while [ $attempt -le $max_retries ]; do
    echo "=== Test attempt $attempt/$max_retries ==="

    if npm test -- --run --reporter=json > test_results_$attempt.json 2>&1; then
      echo "Tests passed on attempt $attempt"
      return 0
    else
      # Extract failed test names for logging
      failed_tests=($(jq -r '.testResults[].assertionResults[] | select(.status=="failed") | .fullName' test_results_$attempt.json 2>/dev/null || echo ""))
      echo "Tests failed on attempt $attempt: ${failed_tests[@]}"
      ((attempt++))
    fi
  done

  echo "ERROR: Tests failed after $max_retries attempts"
  echo "Consistently failing tests suggest a real issue, not flakiness"
  return 1
}
```

### Part 2: Agent Verification Workflow

#### 2.1 Mandatory Verification Step

**Problem:** Agents make code changes but don't confirm the UI issue is resolved

**Solution:** Add mandatory verification step AFTER code changes but BEFORE tests

**Updated Agent Workflow:**
```
1. Read bug report & context
2. Identify root cause
3. Make code changes
4. **NEW: Verify the fix addresses the reported issue**
5. Run test suite
6. Commit if tests pass
```

#### 2.2 Enhanced Agent Prompt

**Current Prompt:**
```
Address bug report bug_20251104_045827_5fd55576.
Description: the image pages are using relative image links. they need the api url.
Route / context: https://imagineer.joshwentworth.com/image/40
```

**Enhanced Prompt:**
```
You are a remediation agent for the Imagineer repository.

BUG REPORT: bug_20251104_045827_5fd55576
ROUTE: https://imagineer.joshwentworth.com/image/40

ISSUE:
- Description: the image pages are using relative image links. they need the api url.
- Expected: Images load using full API URLs (e.g., https://imagineer-api.joshwentworth.com/api/images/40/file)
- Actual: Images broken, using relative paths (e.g., /api/images/40/file)

CONTEXT:
- Screenshot: context/screenshot.png shows broken image placeholder
- Error logs: "Failed to fetch images" (ApiError)
- Network event: GET /api/images/40 returned 200 OK
- Response contains: "download_url": "/api/images/40/file" (relative path - needs normalization)

SUSPECTED ROOT CAUSE:
Image URLs not being normalized with getApiUrl() helper or normalizeGeneratedImage() function

WORKFLOW:
1. Review full context in context.json and screenshot.png
2. Identify the exact component/file causing the issue (likely web/src/pages/ImageDetail.tsx or web/src/lib/api.ts)
3. Implement fix (likely: apply getApiUrl() or normalizeGeneratedImage() to image URLs)
4. **VERIFY YOUR FIX:**
   - Confirm: Does your change normalize the image URL to use the API domain?
   - Check: Are you modifying the RIGHT place where images are fetched/displayed?
   - Validate: Did you handle both download_url AND thumbnail_url if applicable?
   - Review: Read the code you modified - does it make sense for this specific bug?
5. DO NOT commit or push (automation handles this)

QUALITY GATES:
- ❌ FAIL: Changes only to package.json/package-lock.json/build configs
- ❌ FAIL: Changes to unrelated components (e.g., modifying AlbumsTab for an ImageDetail bug)
- ✅ PASS: Changes directly address the reported symptom (broken images → normalized URLs)

The verification suite will run after your changes:
- Frontend: npm lint, tsc, test (may retry up to 3x for flaky tests)
- Backend: black, flake8, pytest

If you cannot complete the work or are unsure about the fix, document why and exit.
DO NOT make speculative changes that don't directly address the reported issue.
```

#### 2.3 Self-Verification Checklist

Add to agent context as `verification_checklist.txt`:

```
Before proceeding to tests, verify your fix:

[ ] Did you identify the ROOT CAUSE from the bug report?
[ ] Does your change DIRECTLY address the reported symptom?
[ ] Did you modify the CORRECT file/component for this bug?
[ ] If UI bug: Did you check the screenshot to understand the visual issue?
[ ] If network error: Did you examine the networkEvents to see what failed?
[ ] Did you avoid making changes to unrelated files (package.json, configs, other components)?
[ ] Can you explain in 1 sentence HOW your change fixes the bug?

Example: "Added getApiUrl() wrapper to image download_url in ImageDetail.tsx to convert relative paths to absolute API URLs"

If you cannot answer "yes" to all questions, re-examine the bug report before proceeding.
```

#### 2.4 Automated Change Validation

Add pre-test validation script to agent_bootstrap.sh:

```bash
validate_changes() {
  local changed_files=$(git diff --cached --name-only)

  # Red flags: only package-lock.json changed
  if [ "$changed_files" == "web/package-lock.json" ] || [ "$changed_files" == "package-lock.json" ]; then
    echo "❌ VALIDATION FAILED: Only package-lock.json was modified"
    echo "This suggests npm install ran but no actual code changes were made"
    return 1
  fi

  # Red flags: no files changed
  if [ -z "$changed_files" ]; then
    echo "❌ VALIDATION FAILED: No files were modified"
    return 1
  fi

  # Get bug context
  local bug_route=$(jq -r '.clientMeta.locationHref' /workspace/context/context.json)
  local bug_desc=$(jq -r '.description' /workspace/context/context.json)

  echo "✓ Files changed: $changed_files"
  echo "✓ Bug route: $bug_route"
  echo "✓ Bug description: $bug_desc"

  # Warn if changing >10 files (likely too broad)
  local file_count=$(echo "$changed_files" | wc -l)
  if [ $file_count -gt 10 ]; then
    echo "⚠️  WARNING: $file_count files changed (expected 1-3 for typical bug fix)"
  fi

  return 0
}

# Add to workflow
run_step "Validate code changes" validate_changes
run_step "Run verification suite" run_tests
```

### Part 3: Post-Fix Validation (Future)

**Vision:** Agent validates fix by running dev server and checking the route

```bash
# Future enhancement
validate_ui_fix() {
  cd "${WORKSPACE_DIR}/web"

  # Start dev server in background
  npm run dev &
  DEV_PID=$!

  # Wait for server to be ready
  timeout 30 bash -c 'until curl -s http://localhost:3000 > /dev/null; do sleep 1; done'

  # Take screenshot of the fixed route
  # (requires playwright or puppeteer)
  npx playwright screenshot "${BUG_ROUTE}" /workspace/artifacts/after_fix.png

  # Kill dev server
  kill $DEV_PID

  echo "Screenshot saved: compare context/screenshot.png (before) with artifacts/after_fix.png (after)"
}
```

This is deferred to Phase 2 due to complexity, but would provide definitive proof the UI issue is resolved.

## Implementation Plan

### Phase 1: Test Stability (Week 1)

**M1.1: Add Test Retries** (2 hours)
- [ ] Update vitest.config.js with retry: 3
- [ ] Add test isolation cleanup to setup.ts
- [ ] Test locally to confirm flaky tests now pass
- [ ] Deploy to agent bootstrap script

**M1.2: Flaky Test Detection** (3 hours)
- [ ] Add retry logic to agent_bootstrap.sh
- [ ] Log which tests fail on each attempt
- [ ] Create flaky test report endpoint
- [ ] Add monitoring alert for tests that fail 2+ times

**M1.3: Test Cleanup** (4 hours)
- [ ] Audit existing tests for shared state
- [ ] Add beforeEach/afterEach cleanup
- [ ] Run tests 10x locally to identify remaining flakes
- [ ] Fix any consistently flaky tests

### Phase 2: Agent Verification (Week 2)

**M2.1: Enhanced Prompts** (3 hours)
- [ ] Update agent_runner.py to generate structured prompts
- [ ] Include expected vs actual behavior
- [ ] Add suspected root cause hints from networkEvents/logs
- [ ] Add quality gate examples

**M2.2: Verification Checklist** (2 hours)
- [ ] Create verification_checklist.txt template
- [ ] Mount in Docker container at /workspace/verification_checklist.txt
- [ ] Update agent prompt to reference checklist

**M2.3: Automated Change Validation** (4 hours)
- [ ] Add validate_changes() function to agent_bootstrap.sh
- [ ] Implement package-lock.json detection
- [ ] Implement file count warnings
- [ ] Add pre-test validation step

**M2.4: Agent Training** (1 hour)
- [ ] Document verification workflow in agent docs
- [ ] Add examples of good vs bad fixes
- [ ] Update CLAUDE.md with verification requirements

### Phase 3: Metrics & Monitoring (Week 3)

**M3.1: Success Metrics Dashboard**
- [ ] Track first-attempt success rate (baseline: 33%)
- [ ] Track test retry rate
- [ ] Track validation failures (package-lock only, no changes, etc.)
- [ ] Track avg time to fix

**M3.2: Quality Metrics**
- [ ] Track "fix actually addresses reported issue" score (manual review)
- [ ] Track reopened bugs (fix didn't work)
- [ ] Track time saved vs manual fixes

## Success Criteria

**Test Stability:**
- ✅ Tests pass consistently (>95% success rate on valid fixes)
- ✅ Flaky test rate < 5% of total test runs
- ✅ Zero rejections due to package-lock.json-only changes

**Fix Quality:**
- ✅ First-attempt success rate improves from 33% to >60%
- ✅ Agents correctly identify root cause in >80% of bugs
- ✅ Zero "unrelated file modified" failures

**Verification:**
- ✅ All automated fixes include explanation of how change addresses bug
- ✅ Agents reference screenshot/logs in their analysis
- ✅ Change validation catches 100% of package-lock-only submissions

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Test retries hide real regressions | High | Limit to 3 retries, log all failures, alert on >2 retries |
| Agents game the verification checklist | Medium | Manual spot-checks, review commit quality weekly |
| Validation is too strict, blocks valid fixes | Medium | Start with warnings, tune thresholds based on data |
| Performance: retries slow down agents | Low | 3 retries acceptable (<5min overhead), monitor duration |

## Open Questions

1. **Should we run visual regression tests?** Playwright can screenshot before/after, but adds 2-3 min overhead per bug
2. **How to handle multi-file bugs?** Some bugs legitimately require changes to 5+ files (e.g., schema updates). Need smarter heuristics.
3. **Agent timeout:** Currently 60min per bug. Is this sufficient for retry logic + validation?

## References

- Test flakiness analysis: See Agent Success Metrics in BUG_REPORT_DB_MIGRATION_PLAN.md
- Current agent bootstrap: `scripts/bug_reports/agent_bootstrap.sh:150-171`
- Vitest config: `web/vitest.config.js`
- Example good fix: commit b283869 (added e.preventDefault() to event handlers)
- Example bad fix: commit d9f5db6 (only modified package-lock.json)
