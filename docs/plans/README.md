# Planning Documents - Index

**Last Updated:** 2025-11-05
**Status:** Reorganized and consolidated

## 📋 Active Planning Documents

These documents contain current, actionable tasks:

### Current Task Lists
- **[BACKEND_TASKS_CONSOLIDATED.md](BACKEND_TASKS_CONSOLIDATED.md)** - All outstanding backend tasks, verified against codebase
  - 10 tasks total (2 P0, 3 P1, 3 P2, 2 P3)
  - Critical: Training-data production setup, prod/dev isolation

- **[FRONTEND_TASKS_CONSOLIDATED.md](FRONTEND_TASKS_CONSOLIDATED.md)** - All outstanding frontend tasks, verified against codebase
  - 11 tasks total (0 P0, 3 P1, 5 P2, 3 P3)
  - Critical: Training runs UI, bug report viewer UI, labeling enhancements

### Strategic Planning
- **[IMPROVEMENT_TASKS_2025Q1.md](IMPROVEMENT_TASKS_2025Q1.md)** - High-level roadmap with 14 major improvement areas
  - Sprint planning for next 4+ weeks
  - Effort estimates and acceptance criteria
  - Solo developer context

### Reference Documents (Keep)
- **[BACKEND_TASKS.md](BACKEND_TASKS.md)** - Original backend backlog (updated 2025-11-01)
- **[FRONTEND_TASKS.md](FRONTEND_TASKS.md)** - Original frontend backlog (updated 2025-11-01)
- **[BACKEND_AUDIT_TASKS.md](BACKEND_AUDIT_TASKS.md)** - Backend audit findings
- **[FRONTEND_AUDIT_TASKS.md](FRONTEND_AUDIT_TASKS.md)** - Frontend audit findings
- **[FRONTEND_CODE_AUDIT.md](FRONTEND_CODE_AUDIT.md)** - Detailed frontend code analysis
- **[REVISED_IMPROVEMENT_PLAN.md](REVISED_IMPROVEMENT_PLAN.md)** - Comprehensive improvement plan (86KB)
- **[BUG_REPORT_TOOL_PLAN.md](BUG_REPORT_TOOL_PLAN.md)** - Bug report system design

---

## 📦 Archived Documents

Completed work and historical documentation moved to `archive/2025-11-05/`:

### Completed Implementations
- `IMPLEMENTATION_COMPLETE.md` - Major feature completions
- `MIGRATION_COMPLETE.md` - Database migration completions
- `PHASE_2_BACKEND_COMPLETE.md` - Backend phase 2 completion
- `PHASE_3_FRONTEND_PROGRESS.md` - Frontend phase 3 updates
- `MIGRATION_CONCERNS_ADDRESSED.md` - Migration issue resolutions

### Completed Migrations
- `BUG_REPORT_DB_MIGRATION_DETAILED_STEPS.md` - Bug report DB migration
- `BUG_REPORT_DB_MIGRATION_PLAN.md` - Bug report migration plan
- `BUG_REPORT_IMPLEMENTATION_PLAN.md` - Bug report implementation (37KB)
- `LEGACY_IMAGE_IMPORT_PLAN.md` - Legacy import implementation
- `SETS_TO_ALBUMS_MIGRATION.md` - Sets→Albums migration
- `TEMPLATE_ALBUM_SEPARATION_PLAN.md` - Template/album separation

### Completed Features
- `NSFW_FILTER_STATUS.md` - NSFW filtering implementation
- `CONSOLIDATED_STATUS.md` - Historical status consolidation
- `SHADCN_REDESIGN_PLAN.md` - UI modernization plan

### Completed Audits
- `CONTRACT_TESTING_INSPECTION_REPORT.md` - Contract testing review
- `FRONTEND_ADAPTATIONS_FOR_BACKEND_AUTH.md` - Auth integration
- `FRONTEND_QUEUE_SECURE_ACCESS.md` - Queue security implementation

---

## 🎯 How to Use This Documentation

### For Active Development
1. **Start here:** [IMPROVEMENT_TASKS_2025Q1.md](IMPROVEMENT_TASKS_2025Q1.md) - See the roadmap
2. **Backend work:** [BACKEND_TASKS_CONSOLIDATED.md](BACKEND_TASKS_CONSOLIDATED.md)
3. **Frontend work:** [FRONTEND_TASKS_CONSOLIDATED.md](FRONTEND_TASKS_CONSOLIDATED.md)

### For Context/History
- Check archived documents in `archive/2025-11-05/`
- Original task lists (BACKEND_TASKS.md, FRONTEND_TASKS.md) for historical context
- Audit documents for codebase analysis

### For Architecture/Design
- See main [ARCHITECTURE.md](../ARCHITECTURE.md) for system design
- See [DEVELOPMENT_WORKFLOW.md](../DEVELOPMENT_WORKFLOW.md) for dev practices
- REVISED_IMPROVEMENT_PLAN.md for detailed improvement strategies

---

## 📊 Current State Summary

### Completed Recently (2025-11-01 to 2025-11-05)
- ✅ NSFW filter controls with persistence
- ✅ ImageCard consolidation across galleries
- ✅ AuthButton migration
- ✅ Tab navigation shadcn/ui migration
- ✅ Typed API client for admin surfaces
- ✅ Bug report system backend
- ✅ Album integration for generated images
- ✅ Development/production environment separation
- ✅ Scraping feature (backend + UI complete)

### High Priority Next (Sprint 1)
1. Training-data repository production setup (1 day)
2. Production/dev environment cleanup (1 day)
3. Training runs UI (3-4 days)

### Active Focus Areas
- **Backend:** Infrastructure setup, API polish, monitoring
- **Frontend:** Admin UIs (training, bug reports), UI modernization
- **DevOps:** Environment isolation, deployment hardening

---

## 🔄 Document Lifecycle

### When to Archive
- Feature/migration is 100% complete and tested
- No remaining todos or open questions
- Implementation verified in production
- Retrospective/lessons learned captured

### When to Update Active Docs
- Weekly review of task progress
- After completing major milestones
- When priorities shift
- After discovering new tasks

### When to Create New Plans
- Starting a new major feature (>1 week)
- Beginning a new sprint/quarter
- After major architectural changes

---

**Maintenance Schedule:**
- Active docs: Review weekly
- Archive: Organized quarterly
- Cleanup: Annually

**Last Major Reorganization:** 2025-11-05
**Next Review:** 2025-11-12 or after Sprint 1 completion
