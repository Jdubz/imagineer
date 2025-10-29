# Shared Types Validation Fix Plan

Created: October 29, 2025  
Owner: Frontend Platform · Status: Draft

## Goal
Keep the frontend Zod schemas aligned with the shared JSON Schema/TypeScript contracts so runtime validation no longer strips legitimate fields (e.g., `email`, `picture`, `is_admin`) or rejects nullable values returned by `/api/auth/me`.

## Tasks

1. **Align AuthStatus Zod Schema (P0)**
   - Update `web/src/lib/schemas.ts:145-149` to mirror `shared/schema/auth_status.json`, including nullable string fields, `is_admin`, `error`, and `message`.
   - Replace the obsolete `username` key with `email` / `name` / `picture` fields that match the generated `AuthStatus` interface.
   - Verify `api.auth.checkAuth()` flows still return full user details and no longer throw `ValidationError`.

2. **Guard Against Schema Drift (P0)**
   - Extend `web/src/__tests__/sharedContract.test.ts` to compare each Zod schema used at runtime (starting with `AuthStatusSchema`) against its JSON Schema equivalent.
   - Ensure the test fails if keys, nullability, or types diverge so future contract changes do not silently regress runtime validation.

3. **Document Schema Synchronisation Process (P1)**
   - Update `docs/plans/FRONTEND_ADAPTATIONS_FOR_BACKEND_AUTH.md` (or create a dedicated note) describing how to add new JSON schemas and regenerate both TypeScript and Zod definitions.
   - Record the need to run `scripts/generate_shared_types.py` whenever a backend contract changes.

## Success Criteria
- `/api/auth/me` responses validate successfully with the Zod schema and expose all fields already present in `AuthStatus`.
- Shared contract tests fail fast if Zod schemas diverge from JSON schema definitions.
- Engineering handbook notes how to keep generated types and runtime schemas in sync.
