# Parallel Work Setup Guide

This guide explains how to set up two agents working simultaneously on different task lists using Git worktrees.

---

## Quick Start

### Agent 1 (Primary - You)
**Location:** Main worktree (`/home/jdubz/Development/imagineer`)
**Tasks:** [AGENT_1_TASKS.md](./AGENT_1_TASKS.md)
**Focus:** Training & Scraping Systems

```bash
# You're already in the right place
cd /home/jdubz/Development/imagineer

# Pull latest
git pull origin develop

# Start working on Agent 1 tasks
# (See AGENT_1_TASKS.md for details)
```

### Agent 2 (Secondary - Separate Claude Instance)
**Location:** New worktree (`/home/jdubz/Development/imagineer-agent2`)
**Tasks:** [AGENT_2_TASKS.md](./AGENT_2_TASKS.md)
**Focus:** Image Management & Labeling Systems

```bash
# Create a new worktree from the main repo
cd /home/jdubz/Development/imagineer
git worktree add ../imagineer-agent2 develop

# Agent 2 works here
cd ../imagineer-agent2

# Verify it's a separate working directory
git status
```

---

## What is a Git Worktree?

A Git worktree allows multiple working directories for the same repository. This means:

- ✅ Two agents can edit files simultaneously
- ✅ Each has their own working directory
- ✅ Both share the same Git history
- ✅ Changes can be committed independently
- ✅ Merging happens normally via Git

**Traditional approach (doesn't work well):**
```
repo/
  - Only one working directory
  - Can't have two people editing same repo
  - Would need to clone twice
```

**Worktree approach (works great):**
```
imagineer/          ← Agent 1 works here
imagineer-agent2/   ← Agent 2 works here
  .git/             ← Shared Git data
```

---

## Detailed Setup Instructions

### Step 1: Create the Worktree (Run Once)

```bash
# From the main imagineer directory
cd /home/jdubz/Development/imagineer

# Create a new worktree at ../imagineer-agent2 from develop branch
git worktree add ../imagineer-agent2 develop

# Verify creation
git worktree list
# Should output:
# /home/jdubz/Development/imagineer        <commit-hash> [develop]
# /home/jdubz/Development/imagineer-agent2 <commit-hash> [develop]
```

### Step 2: Start Agent 1 (Primary)

```bash
# Stay in main directory
cd /home/jdubz/Development/imagineer

# View your task list
cat docs/plans/AGENT_1_TASKS.md

# Start with Task 1: Training Album Persistence
# (Follow detailed instructions in AGENT_1_TASKS.md)
```

### Step 3: Start Agent 2 (Secondary)

**Option A: New Terminal Window**
```bash
cd /home/jdubz/Development/imagineer-agent2

# View task list
cat docs/plans/AGENT_2_TASKS.md

# Start with Task 1: Consolidate Duplicate Endpoints
```

**Option B: New Claude Code Session**
```bash
# In a new Claude Code session, run:
cd /home/jdubz/Development/imagineer-agent2
claude
# Then tell Claude to follow AGENT_2_TASKS.md
```

---

## Working in Parallel

### File Conflict Matrix

Here's what each agent touches:

| File | Agent 1 | Agent 2 | Conflict Risk |
|------|---------|---------|---------------|
| `server/routes/training.py` | ✅ | ❌ | None |
| `server/routes/scraping.py` | ✅ | ❌ | None |
| `server/tasks/training.py` | ✅ | ❌ | None |
| `server/tasks/scraping.py` | ✅ | ❌ | None |
| `server/routes/images.py` | ❌ | ✅ | None |
| `server/routes/albums.py` | ❌ | ✅ | None |
| `server/tasks/labeling.py` | ❌ | ✅ | None |
| `server/api.py` | ⚠️ | ⚠️ | **LOW** (different sections) |
| `server/celery_app.py` | ❌ | ✅ | None |
| `web/src/components/*` | ❌ | ✅ | None |
| `tests/backend/*` | ❌ | ✅ | None |
| `config.yaml` | ✅ | ❌ | None |

**Minimal Conflicts Expected:** Only `server/api.py` is touched by both, but in different sections (Training vs Images).

---

## Commit Strategy

### Agent 1 Commits
```bash
# After completing Task 1
git add server/routes/training.py
git commit -m "fix: Persist album_ids in training run creation

- Add album_ids field to TrainingRun creation endpoint
- Ensure album_ids are committed to database
- Fix 'No albums specified' error in train_lora_task

Related: AGENT_1_TASKS.md Task 1"

# Push to develop
git push origin develop
```

### Agent 2 Commits
```bash
# After completing Task 1
git add server/api.py server/routes/images.py
git commit -m "refactor: Consolidate duplicate image endpoints

- Remove duplicate image/thumbnail endpoints from api.py
- Use images blueprint exclusively
- Ensure all functionality preserved
- Update tests to use blueprint routes

Related: AGENT_2_TASKS.md Task 1"

# Try to push
git push origin develop
```

---

## Merging Strategy

### Recommended Order

**Step 1: Agent 1 finishes first tasks and pushes**
```bash
# Agent 1 (in main imagineer/)
git add server/routes/training.py server/tasks/training.py server/tasks/scraping.py config.yaml
git commit -m "fix: Critical training and scraping fixes (Tasks 1-2)"
git push origin develop
```

**Step 2: Agent 2 pulls and merges**
```bash
# Agent 2 (in imagineer-agent2/)
# First, commit local changes
git add server/api.py server/routes/images.py server/celery_app.py
git commit -m "refactor: Consolidate endpoints and fix task naming (Tasks 1-2)"

# Pull Agent 1's changes
git pull origin develop

# If conflicts (unlikely):
# - Edit conflicting files
# - Run: git add <resolved-files>
# - Run: git commit

# Push Agent 2's changes
git push origin develop
```

**Step 3: Agent 1 pulls Agent 2's changes**
```bash
# Agent 1 (in main imagineer/)
git pull origin develop

# Continue with remaining tasks
```

### Handling Conflicts (If They Occur)

If `git pull` reports conflicts:

1. **Check conflict location:**
```bash
git status
# Shows: "both modified: server/api.py"
```

2. **Open file and look for conflict markers:**
```python
<<<<<<< HEAD
# Your changes (Agent 2's version)
=======
# Their changes (Agent 1's version)
>>>>>>> origin/develop
```

3. **Resolve manually:**
- Keep both changes if they're in different sections
- Choose one if they conflict directly
- Test that the resolved version works

4. **Mark as resolved:**
```bash
git add server/api.py
git commit -m "Merge: Resolve conflict in api.py"
git push origin develop
```

---

## Communication Between Agents

### Update Status Document

Both agents should update `CONSOLIDATED_STATUS.md` when completing tasks:

```bash
# After completing a task
nano docs/plans/CONSOLIDATED_STATUS.md

# Mark task as complete:
# Change: "⚠️ Outstanding Issues"
# To:     "✅ Completed"

git add docs/plans/CONSOLIDATED_STATUS.md
git commit -m "docs: Mark Task X as complete"
```

### Progress Tracking

Create a shared progress file:

```bash
# Agent 1 or Agent 2 creates this
echo "# Parallel Work Progress

## Agent 1 (Training & Scraping)
- [ ] Task 1: Training Album Persistence
- [ ] Task 2: SCRAPED_OUTPUT_PATH Init
- [ ] Task 3: Training Logs Streaming
- [ ] Task 4: Auto-Register LoRAs
- [ ] Task 5: Training Cleanup

## Agent 2 (Images & Labeling)
- [ ] Task 1: Consolidate Endpoints
- [ ] Task 2: Fix Celery Task Naming
- [ ] Task 3: Frontend Labeling UI
- [ ] Task 4: Update Async Tests
- [ ] Task 5: Frontend Tests
" > docs/plans/PROGRESS.md

git add docs/plans/PROGRESS.md
git commit -m "docs: Add parallel work progress tracker"
git push origin develop
```

Each agent updates their section when completing tasks.

---

## Testing While Working in Parallel

### Agent 1 Tests
```bash
# In main imagineer/
source venv/bin/activate

# Test training fixes
pytest tests/backend/ -k training -v

# Test scraping fixes
pytest tests/backend/ -k scraping -v

# Start services to test manually
python server/api.py
```

### Agent 2 Tests
```bash
# In imagineer-agent2/
source venv/bin/activate

# Test image endpoint changes
pytest tests/backend/test_api.py -k images -v

# Test labeling
pytest tests/backend/test_phase3_labeling.py -v

# Test frontend
cd web && npm test
```

**Important:** Both can run tests simultaneously since they're in different directories.

---

## Cleanup After Completion

### When All Tasks Are Done

**Agent 2 worktree cleanup:**
```bash
# From main repo
cd /home/jdubz/Development/imagineer

# Remove the worktree (after all changes are merged)
git worktree remove ../imagineer-agent2

# Or if you want to keep it for future work:
# Just leave it, it will stay in sync
```

### Verify Everything Merged

```bash
# In main repo
git log --oneline --graph --all | head -20

# Should see both Agent 1 and Agent 2 commits
```

---

## Troubleshooting

### "Cannot lock ref" error
```bash
# Worktree might be corrupted
cd /home/jdubz/Development/imagineer
git worktree prune
git worktree add ../imagineer-agent2 develop
```

### "Changes would be overwritten" on pull
```bash
# Commit or stash your changes first
git stash
git pull
git stash pop
```

### Agent 2 can't push to develop
```bash
# Agent 1 pushed first, need to pull and merge
git pull --rebase origin develop
git push origin develop
```

### Both agents modified same line
```bash
# Manual conflict resolution required
# See "Handling Conflicts" section above
```

---

## Summary

1. **Setup:** Create worktree once
2. **Work:** Each agent follows their task list independently
3. **Commit:** Commit frequently to local worktree
4. **Coordinate:** Agent 1 pushes first, Agent 2 pulls and merges
5. **Complete:** All tasks done, worktree can be removed

**Estimated Total Time:**
- Agent 1: 7-8 hours
- Agent 2: 9-10 hours
- Can complete in 1 day if both work in parallel

**Result:** ~85% → 100% feature completion! 🎉

---

**Questions?** Check Git worktree docs: https://git-scm.com/docs/git-worktree
