# Contract Testing System

**Last Updated:** 2025-10-28

## Overview

Imagineer implements a **schema-driven contract testing system** to ensure type safety and API consistency between the Python backend and TypeScript frontend. This prevents runtime type errors and ensures both sides of the application agree on data structures.

---

## Architecture

### 1. Schema-First Design

The system follows a schema-first approach:

```
┌─────────────────────────────────────────────────────────────┐
│                   JSON Schema Definition                     │
│              (shared/schema/*.json)                          │
│                                                              │
│  Single source of truth for API contracts                   │
└────────────────┬─────────────────────────────────────────┬──┘
                 │                                          │
                 v                                          v
    ┌────────────────────────┐              ┌─────────────────────────┐
    │  TypeScript Interface  │              │  Python TypedDict       │
    │  (web/src/types/)      │              │  (server/shared_types)  │
    │                        │              │                         │
    │  export interface      │              │  class AuthStatus       │
    │    AuthStatus {        │              │    TypedDict(...):      │
    │    authenticated: bool │              │    authenticated: bool  │
    │    email?: string      │              │    email: str | None    │
    │  }                     │              │                         │
    └────────────┬───────────┘              └───────────┬─────────────┘
                 │                                      │
                 │                                      │
                 v                                      v
    ┌────────────────────────┐              ┌─────────────────────────┐
    │  Frontend Code         │              │  Backend Code           │
    │  (React/TypeScript)    │◄────HTTP────►│  (Flask/Python)        │
    │                        │    JSON      │                         │
    │  Types enforced at     │              │  Types enforced at      │
    │  compile time          │              │  type check time        │
    └────────────────────────┘              └─────────────────────────┘
                 │                                      │
                 │                                      │
                 └──────────────┬───────────────────────┘
                                │
                                v
                    ┌────────────────────────┐
                    │  Contract Tests        │
                    │  (tests/backend/)      │
                    │                        │
                    │  Validates:            │
                    │  • Schema sync         │
                    │  • Runtime responses   │
                    │  • Type correctness    │
                    └────────────────────────┘
```

---

## Components

### 1. JSON Schemas (`shared/schema/*.json`)

**Purpose:** Single source of truth for API data structures

**Location:** `shared/schema/`

**Format:** JSON Schema (subset)

**Example:** `auth_status.json`
```json
{
  "name": "AuthStatus",
  "description": "Response payload returned by /api/auth/me.",
  "type": "object",
  "properties": {
    "authenticated": { "type": "boolean" },
    "email": { "type": ["string", "null"] },
    "name": { "type": ["string", "null"] },
    "role": { "type": ["string", "null"] },
    "is_admin": { "type": ["boolean", "null"] }
  },
  "required": ["authenticated"]
}
```

**Supported Features:**
- ✅ Primitive types: `string`, `boolean`, `number`, `integer`, `null`
- ✅ Union types: `["string", "null"]` → `string | null`
- ✅ Arrays: `{"type": "array", "items": {...}}`
- ✅ Objects: `{"type": "object"}`
- ✅ Enums: `{"enum": ["value1", "value2"]}`
- ✅ Required vs optional fields
- ✅ Descriptions and documentation

---

### 2. Type Generator (`scripts/generate_shared_types.py`)

**Purpose:** Generates TypeScript interfaces and Python TypedDicts from schemas

**Usage:**
```bash
python scripts/generate_shared_types.py
```

**Outputs:**
1. **TypeScript:** `web/src/types/shared.ts`
2. **Python:** `server/shared_types.py`

**Example Generation:**

From schema:
```json
{
  "name": "AuthStatus",
  "properties": {
    "authenticated": {"type": "boolean"},
    "email": {"type": ["string", "null"]}
  },
  "required": ["authenticated"]
}
```

**TypeScript Output:**
```typescript
export interface AuthStatus {
  authenticated: boolean;
  email?: string | null;
}
```

**Python Output:**
```python
class AuthStatusTypedDict(TypedDict, total=False):
    """Response payload returned by /api/auth/me."""
    authenticated: Required[bool]
    email: NotRequired[str | None]
```

---

### 3. Contract Tests (`tests/backend/test_shared_contracts.py`)

**Purpose:** Enforce contracts at test time

**Test Coverage:**

#### Test 1: Schema Sync Verification
```python
def test_python_and_typescript_shared_types_are_in_sync():
    """Ensure generated types match current schemas."""
```

**What it checks:**
- ✅ Generated TypeScript matches expected output
- ✅ Generated Python matches expected output
- ✅ No manual edits to generated files
- ✅ Schema changes trigger regeneration

**Failure mode:** Test fails if you modify schemas but forget to run generator

---

#### Test 2: Runtime Response Validation
```python
@pytest.mark.usefixtures("mock_admin_auth")
def test_auth_me_authenticated_response_matches_schema(client):
    """Authenticated /api/auth/me response matches schema."""
```

**What it checks:**
- ✅ API response has all required fields
- ✅ API response has no unexpected fields
- ✅ Field types match schema definitions
- ✅ Enum values are valid
- ✅ Arrays contain correct item types

**Failure mode:** Test fails if API returns wrong shape/types

---

## How to Add a New Contract

### Step 1: Create Schema

Create `shared/schema/my_endpoint.json`:
```json
{
  "name": "ImageMetadata",
  "description": "Image metadata response from /api/images/{id}",
  "type": "object",
  "properties": {
    "id": { "type": "integer" },
    "filename": { "type": "string" },
    "width": { "type": "integer" },
    "height": { "type": "integer" },
    "is_nsfw": { "type": "boolean" },
    "created_at": { "type": "string" },
    "tags": {
      "type": "array",
      "items": { "type": "string" }
    }
  },
  "required": ["id", "filename", "is_nsfw"]
}
```

### Step 2: Generate Types

```bash
python scripts/generate_shared_types.py
```

This updates:
- `web/src/types/shared.ts`
- `server/shared_types.py`

### Step 3: Add Contract Test

In `tests/backend/test_shared_contracts.py`:
```python
def test_image_metadata_response_matches_schema(client):
    """GET /api/images/{id} response matches schema."""
    schema = _load_schema("image_metadata")

    # Create test image first
    # ... setup code ...

    response = client.get(f"/api/images/{image_id}")
    assert response.status_code == 200
    payload = response.get_json()

    assert isinstance(payload, dict)
    _validate_against_schema(payload, schema)
```

### Step 4: Use Types in Code

**Backend (server/routes/images.py):**
```python
from server.shared_types import ImageMetadataTypedDict

@images_bp.route("/<int:image_id>", methods=["GET"])
def get_image(image_id: int) -> ImageMetadataTypedDict:
    image = Image.query.get_or_404(image_id)

    # Type checker ensures this matches schema
    return {
        "id": image.id,
        "filename": image.filename,
        "width": image.width,
        "height": image.height,
        "is_nsfw": image.is_nsfw,
        "created_at": image.created_at.isoformat(),
        "tags": [label.label_text for label in image.labels]
    }
```

**Frontend (web/src/components/ImageViewer.tsx):**
```typescript
import { ImageMetadata } from '../types/shared';

async function fetchImageMetadata(id: number): Promise<ImageMetadata> {
  const response = await fetch(`/api/images/${id}`);
  return response.json(); // TypeScript knows the shape
}

function ImageViewer({ imageId }: { imageId: number }) {
  const [metadata, setMetadata] = useState<ImageMetadata | null>(null);

  // TypeScript autocomplete works here:
  return <div>
    <h2>{metadata?.filename}</h2>
    <p>Size: {metadata?.width}x{metadata?.height}</p>
    <p>NSFW: {metadata?.is_nsfw ? 'Yes' : 'No'}</p>
  </div>;
}
```

---

## Benefits

### 1. Type Safety Across Stack

**Without contracts:**
```typescript
// Frontend
const data = await response.json(); // any type
console.log(data.authenitcated); // Typo! Runtime error
```

**With contracts:**
```typescript
// Frontend
const data: AuthStatus = await response.json();
console.log(data.authenticated); // ✅ TypeScript catches typo at compile time
```

### 2. Catch Breaking Changes Early

**Scenario:** Backend removes `email` field

**Without contracts:**
- Frontend breaks at runtime
- Users see errors
- Hard to debug

**With contracts:**
- Contract test fails immediately
- CI pipeline blocks merge
- Fix before deployment

### 3. Documentation as Code

Schemas serve as machine-readable documentation:
- No drift between docs and reality
- Always up to date
- Self-documenting API

### 4. Refactoring Confidence

When changing API shape:
1. Update schema
2. Regenerate types
3. Type checker shows all affected code
4. Fix all issues
5. Tests confirm correctness

---

## Current Coverage

### Implemented Contracts ✅

| Schema | Endpoint | Frontend Usage | Tests |
|--------|----------|----------------|-------|
| `auth_status` | `/api/auth/me` | `AuthButton.tsx` | ✅ 2 tests |

### Recommended Additions 📋

High-value contracts to add:

1. **Image Metadata**
   - Schema: `image_metadata.json`
   - Endpoint: `/api/images/{id}`
   - Used by: Gallery, ImageGrid, AlbumsTab

2. **Album Details**
   - Schema: `album_details.json`
   - Endpoint: `/api/albums/{id}`
   - Used by: AlbumsTab, TrainingTab

3. **Training Run Status**
   - Schema: `training_run.json`
   - Endpoint: `/api/training/runs/{id}`
   - Used by: TrainingTab

4. **Scrape Job Status**
   - Schema: `scrape_job.json`
   - Endpoint: `/api/scraping/jobs/{id}`
   - Used by: ScrapingTab

5. **Label Data**
   - Schema: `image_label.json`
   - Endpoint: `/api/labeling/image/{id}` response
   - Used by: LabelingPanel (when implemented)

---

## Testing Strategy

### Unit Tests
- ✅ `test_python_and_typescript_shared_types_are_in_sync`
  - Ensures no drift between schemas and generated code

### Integration Tests
- ✅ `test_auth_me_authenticated_response_matches_schema`
- ✅ `test_auth_me_public_response_matches_schema`
  - Validates actual API responses

### CI/CD Integration

**Pre-commit hook:**
```bash
# Verify types are in sync
python scripts/generate_shared_types.py
git diff --exit-code web/src/types/shared.ts server/shared_types.py
```

**GitHub Actions:**
```yaml
- name: Validate contract sync
  run: |
    python scripts/generate_shared_types.py
    git diff --exit-code web/src/types/shared.ts server/shared_types.py

- name: Run contract tests
  run: pytest tests/backend/test_shared_contracts.py -v
```

---

## Best Practices

### DO ✅

1. **Use contracts for core API endpoints**
   - User-facing data
   - Cross-cutting concerns (auth, errors)
   - Complex nested structures

2. **Update schema when changing API**
   - Change schema first
   - Regenerate types
   - Update implementation
   - Tests validate correctness

3. **Keep schemas simple**
   - Focus on structure, not validation rules
   - Use TypedDict, not Pydantic models
   - Schema is for shape, not business logic

4. **Run generator after schema changes**
   ```bash
   python scripts/generate_shared_types.py
   ```

### DON'T ❌

1. **Don't manually edit generated files**
   - `web/src/types/shared.ts` - AUTO-GENERATED
   - `server/shared_types.py` - AUTO-GENERATED
   - Edit schemas instead

2. **Don't add contracts for internal endpoints**
   - Admin-only endpoints with complex logic
   - Endpoints that change frequently
   - One-off experimental features

3. **Don't over-specify**
   - Avoid complex validation in schemas
   - Use separate validation layer (Pydantic, etc.)
   - Schema = type shape, not business rules

4. **Don't skip tests**
   - Always add test for new contract
   - Verify both success and error cases
   - Test with real data, not mocks

---

## Troubleshooting

### Problem: Test fails with "out of date" message

**Cause:** Schema was modified but types weren't regenerated

**Solution:**
```bash
python scripts/generate_shared_types.py
git add web/src/types/shared.ts server/shared_types.py
```

---

### Problem: API response fails validation

**Cause:** Backend returns different shape than schema

**Solution:**
1. Check error message for specific field
2. Either:
   - Fix backend to match schema, OR
   - Update schema to match new reality
3. Regenerate types
4. Fix frontend code if needed

---

### Problem: TypeScript compilation errors after regenerating

**Cause:** Schema change broke frontend code

**Solution:**
1. TypeScript compiler shows all affected locations
2. Update each location to use new type
3. This is a **good thing** - catching errors at compile time!

---

## Future Enhancements

### Planned Features

1. **OpenAPI/Swagger Generation**
   - Generate OpenAPI spec from schemas
   - Interactive API documentation
   - Client SDK generation

2. **Runtime Validation**
   - Validate requests/responses at runtime
   - Catch data corruption early
   - Better error messages

3. **Schema Versioning**
   - Track schema versions
   - Support migration paths
   - Backward compatibility checks

4. **More Test Coverage**
   - All major endpoints have contracts
   - Error response schemas
   - WebSocket message schemas

---

## References

- **JSON Schema:** https://json-schema.org/
- **TypedDict:** https://peps.python.org/pep-0589/
- **TypeScript Types:** https://www.typescriptlang.org/docs/handbook/2/everyday-types.html

---

## Conclusion

The contract testing system provides:
- ✅ Type safety across the full stack
- ✅ Early detection of breaking changes
- ✅ Self-documenting API
- ✅ Refactoring confidence

It's a lightweight system (< 300 lines of code) that prevents entire classes of bugs.

**Status:** Operational with 1 contract (`auth_status`), ready to expand to all major endpoints.

---

**Maintained by:** Imagineer Project Team
**Last Test Run:** All 3 tests passing ✅
