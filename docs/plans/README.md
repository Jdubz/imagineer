# Planning Documents Index

This directory contains all planning and improvement documents for the Imagineer project.

## 📋 Active Documents (Start Here)

### [CONSOLIDATED_STATUS.md](./CONSOLIDATED_STATUS.md) 🎯
**The single source of truth** for implementation status. Created 2025-10-28.

- Complete reconciliation of all plans against current codebase
- Phase-by-phase completion status
- Prioritized list of outstanding work
- Testing strategy and recommendations
- **Read this first for current project status**

### [REVISED_IMPROVEMENT_PLAN.md](./REVISED_IMPROVEMENT_PLAN.md)
**The actual roadmap** aligned with project goals (albums, labeling, scraping, training). ~85% complete.

- Phase 1: Foundation & Security ✅
- Phase 2: Album System ✅
- Phase 3: AI Labeling ⚠️ (backend done, frontend gaps)
- Phase 4: Web Scraping ⚠️ (config issue)
- Phase 5: Training Pipeline ⚠️ (persistence issues)

---

## 📚 Superseded Documents (Reference Only)

These documents were accurate when written but have been replaced by CONSOLIDATED_STATUS.md:

### [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md)
Previous status snapshot from 2025-10-28. Issues listed are now tracked in CONSOLIDATED_STATUS.md.

### [COMPREHENSIVE_IMPROVEMENT_PLAN.md](./COMPREHENSIVE_IMPROVEMENT_PLAN.md)
Original 28-vulnerability security audit and improvement plan. Superseded by REVISED_IMPROVEMENT_PLAN.md which focuses on actual project goals (training pipeline, not just generation).

**Still useful for:**
- Security audit findings reference
- Code quality metrics baseline
- General architectural best practices

### [CLAUDE_CLI_MIGRATION.md](./CLAUDE_CLI_MIGRATION.md) ✅ COMPLETED
Plan for migrating from Anthropic API to Claude CLI in Docker for image labeling. This migration is **complete** as of October 2025.

### [PRODUCTION_FIXES.md](./PRODUCTION_FIXES.md) ✅ COMPLETED
OAuth HTTPS fixes and thumbnail diagnostics from October 27, 2025. Issues resolved.

---

## 🔒 Deployment & Security

### [SECURE_AUTHENTICATION_PLAN.md](../deployment/SECURE_AUTHENTICATION_PLAN.md)
Authentication strategy comparison (v1.0 password gate → v2.0 session auth → v3.0 OAuth).

**Current Status:** Phase 3 (Google OAuth) implemented, legacy password gate removed.

---

## 🎯 Quick Reference: What to Read

| Scenario | Document to Read |
|----------|------------------|
| "What's the current status?" | **CONSOLIDATED_STATUS.md** |
| "What needs to be built next?" | **CONSOLIDATED_STATUS.md** (Recommended Next Actions) |
| "What was the original plan?" | REVISED_IMPROVEMENT_PLAN.md |
| "What security issues were found?" | COMPREHENSIVE_IMPROVEMENT_PLAN.md (Security section) |
| "How does auth work?" | SECURE_AUTHENTICATION_PLAN.md + CONSOLIDATED_STATUS.md |

---

## 📊 Overall Progress Summary

From CONSOLIDATED_STATUS.md:

- **Phase 1 (Foundation & Security):** 95% ✅
- **Phase 2 (Album System):** 90% ✅
- **Phase 3 (AI Labeling):** 70% ⚠️
- **Phase 4 (Web Scraping):** 80% ⚠️
- **Phase 5 (Training Pipeline):** 75% ⚠️

**Overall:** ~85% complete, 2-3 days of work to production-ready MVP

---

## 🔧 Critical Next Actions

From CONSOLIDATED_STATUS.md (see full document for details):

1. 🔴 **Fix training album persistence** (server/routes/training.py)
2. 🔴 **Initialize SCRAPED_OUTPUT_PATH** (server/tasks/scraping.py:22)
3. 🔴 **Consolidate duplicate endpoints** (api.py vs routes/images.py)
4. 🟡 **Implement frontend labeling UI** (web/src/components/)
5. 🟡 **Fix Celery task naming** (celery_app.py, tasks/*.py)
6. 🟡 **Implement training logs streaming** (routes/training.py)

---

## 🚀 Ready to Work? Parallel Task Lists

### [AGENT_1_TASKS.md](./AGENT_1_TASKS.md) - Training & Scraping
**For:** Primary agent (main worktree)
**Time:** 7-8 hours
**Focus:** Training album persistence, scraping config, logs streaming

### [AGENT_2_TASKS.md](./AGENT_2_TASKS.md) - Images & Labeling
**For:** Secondary agent (separate worktree)
**Time:** 9-10 hours
**Focus:** Endpoint consolidation, Celery naming, frontend labeling UI

### [PARALLEL_WORK_SETUP.md](./PARALLEL_WORK_SETUP.md) - Setup Guide
**How to:** Set up Git worktrees for simultaneous development
**Includes:** Conflict management, merge strategy, communication

---

**Last Updated:** 2025-10-28
**Maintained By:** Project team
**Next Review:** After completing critical fixes
