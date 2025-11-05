# Sets → Albums Migration Plan

## Executive Summary

Consolidate the CSV-based "sets" system into the database-backed "albums" system. A set is conceptually just an album with a generation template. This unifies the codebase and enables powerful features like:

- Set templates can be managed through the UI
- Generated images automatically link to their source album
- Training can use set-based albums directly
- Labeling and NSFW filtering work on set images
- No file system dependency for set configuration

## Current Architecture

### Sets (CSV-based)
**Location:** `/mnt/speedy/imagineer/sets/`

**Structure:**
```
sets/
├── card_deck.csv          # 54 playing cards
├── tarot_deck.csv         # 22 Major Arcana
├── zodiac.csv             # 12 zodiac signs
└── config.yaml            # Per-set generation settings
```

**config.yaml Example:**
```yaml
card_deck:
  name: Playing Card Deck
  description: A complete deck of 54 playing cards...
  csv_path: data/sets/card_deck.csv
  base_prompt: "PlayingCards. The face of a single..."
  prompt_template: '{value} of {suit}. CARD LAYOUT: {visual_layout}...'
  style_suffix: traditional playing card design...
  width: 512
  height: 720
  negative_prompt: multiple cards, stack of cards...
  loras:
    - path: /mnt/speedy/imagineer/models/lora/...
      weight: 0.5
```

**Code References:**
- `server/api.py:525-558` - `load_sets_config()`
- `server/api.py:561-571` - `get_set_config()`
- `server/api.py:647-686` - `load_set_data()` - loads CSV
- `server/api.py:1150-1208` - `/api/sets` - list sets endpoint
- `server/api.py:1211-1266` - `/api/generate/batch` - batch generation

### Albums (Database-backed)
**Location:** `server/database.py:120-168`

**Schema:**
```python
class Album(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    is_public = db.Column(db.Boolean, default=False)
    is_training_source = db.Column(db.Boolean, default=False)
    created_by = db.Column(db.String(255))

    # Generation context (already exists!)
    generation_prompt = db.Column(db.Text)
    generation_config = db.Column(db.Text)  # JSON
```

**Key Features:**
- Many-to-many relationship with images via `AlbumImage`
- Privacy controls (`is_public`)
- Training source flag (`is_training_source`)
- **Already has generation fields!** ✅

## Migration Strategy

### Phase 1: Extend Album Model (Database Schema)

Add new fields to support set-like templates:

```python
class Album(db.Model):
    # ... existing fields ...

    # Set template fields (NEW)
    is_set_template = db.Column(db.Boolean, default=False)
    csv_data = db.Column(db.Text)  # JSON: list of template items
    base_prompt = db.Column(db.Text)
    prompt_template = db.Column(db.Text)
    style_suffix = db.Column(db.Text)
    example_theme = db.Column(db.Text)
    lora_config = db.Column(db.Text)  # JSON: [{path, weight}, ...]
```

**Migration Script:**
```python
# server/migrations/add_set_template_fields.py
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('albums', sa.Column('is_set_template', sa.Boolean(), server_default='0'))
    op.add_column('albums', sa.Column('csv_data', sa.Text(), nullable=True))
    op.add_column('albums', sa.Column('base_prompt', sa.Text(), nullable=True))
    op.add_column('albums', sa.Column('prompt_template', sa.Text(), nullable=True))
    op.add_column('albums', sa.Column('style_suffix', sa.Text(), nullable=True))
    op.add_column('albums', sa.Column('example_theme', sa.Text(), nullable=True))
    op.add_column('albums', sa.Column('lora_config', sa.Text(), nullable=True))

def downgrade():
    op.drop_column('albums', 'lora_config')
    op.drop_column('albums', 'example_theme')
    op.drop_column('albums', 'style_suffix')
    op.drop_column('albums', 'prompt_template')
    op.drop_column('albums', 'base_prompt')
    op.drop_column('albums', 'csv_data')
    op.drop_column('albums', 'is_set_template')
```

### Phase 2: Data Migration Script

Import existing sets into the database:

```python
# scripts/migrate_sets_to_albums.py
import csv
import json
import yaml
from pathlib import Path
from server.database import db, Album
from server.api import app

def migrate_sets_to_albums():
    """Migrate CSV-based sets to database albums"""

    sets_dir = Path("/mnt/speedy/imagineer/sets")
    config_path = sets_dir / "config.yaml"

    with app.app_context():
        # Load sets config
        with open(config_path) as f:
            sets_config = yaml.safe_load(f)

        for set_id, set_config in sets_config.items():
            print(f"Migrating set: {set_id}")

            # Check if album already exists
            existing = Album.query.filter_by(name=set_config['name']).first()
            if existing:
                print(f"  ⚠️  Album '{set_config['name']}' already exists, skipping")
                continue

            # Load CSV data
            csv_path = sets_dir / f"{set_id}.csv"
            if not csv_path.exists():
                print(f"  ❌ CSV not found: {csv_path}")
                continue

            csv_items = []
            with open(csv_path) as f:
                reader = csv.DictReader(f)
                csv_items = list(reader)

            # Create album with set template
            album = Album(
                name=set_config['name'],
                description=set_config.get('description', ''),
                is_set_template=True,
                is_public=True,  # Sets were public by default
                csv_data=json.dumps(csv_items),
                base_prompt=set_config.get('base_prompt'),
                prompt_template=set_config.get('prompt_template'),
                style_suffix=set_config.get('style_suffix'),
                example_theme=set_config.get('example_theme'),
                generation_config=json.dumps({
                    'width': set_config.get('width', 512),
                    'height': set_config.get('height', 512),
                    'negative_prompt': set_config.get('negative_prompt', ''),
                }),
                lora_config=json.dumps(set_config.get('loras', [])),
                created_by='system'
            )

            db.session.add(album)
            print(f"  ✅ Created album with {len(csv_items)} template items")

        db.session.commit()
        print("\n✨ Migration complete!")

if __name__ == '__main__':
    migrate_sets_to_albums()
```

### Phase 3: Update API Endpoints

#### 3.1 Create Unified Albums API

**New endpoint:** `/api/albums/{album_id}/generate/batch`

```python
@albums_bp.route("/<int:album_id>/generate/batch", methods=["POST"])
@require_admin
def generate_batch_from_album(album_id):
    """Generate all items from a set template album"""
    album = db.session.get(Album, album_id)

    if not album:
        return jsonify({"error": "Album not found"}), 404

    if not album.is_set_template:
        return jsonify({"error": "Album is not a set template"}), 400

    # Parse CSV data
    template_items = json.loads(album.csv_data or "[]")
    if not template_items:
        return jsonify({"error": "No template items in album"}), 400

    # Parse generation config
    gen_config = json.loads(album.generation_config or "{}")
    loras = json.loads(album.lora_config or "[]")

    # Get user theme override
    data = request.json or {}
    user_theme = data.get("user_theme", "")

    # Queue generation jobs
    jobs = []
    for item in template_items:
        # Build prompt from template
        prompt = build_prompt(
            base=album.base_prompt,
            template=album.prompt_template,
            item=item,
            theme=user_theme,
            suffix=album.style_suffix
        )

        job = queue_generation_job(
            prompt=prompt,
            album_id=album.id,  # Link to source album
            **gen_config,
            loras=loras
        )
        jobs.append(job)

    return jsonify({
        "message": f"Queued {len(jobs)} generation jobs",
        "album_id": album.id,
        "jobs": [j.to_dict() for j in jobs]
    }), 201
```

#### 3.2 Deprecate Old Sets Endpoints

```python
@app.route("/api/sets", methods=["GET"])
def list_sets_deprecated():
    """DEPRECATED: Use /api/albums?is_set_template=true instead"""
    logger.warning("Deprecated endpoint /api/sets called")

    # Redirect to albums endpoint
    albums = Album.query.filter_by(is_set_template=True).all()

    # Format as old sets response for backward compatibility
    sets = []
    for album in albums:
        gen_config = json.loads(album.generation_config or "{}")
        sets.append({
            "id": album.name.lower().replace(" ", "_"),  # Backward compat
            "name": album.name,
            "description": album.description,
            "item_count": len(json.loads(album.csv_data or "[]")),
            "width": gen_config.get('width', 512),
            "height": gen_config.get('height', 512),
            "example_theme": album.example_theme,
        })

    return jsonify({"sets": sets, "_deprecated": True})

@app.route("/api/generate/batch", methods=["POST"])
@require_admin
def generate_batch_deprecated():
    """DEPRECATED: Use /api/albums/{id}/generate/batch instead"""
    data = request.json or {}
    set_name = data.get("set_name")

    if not set_name:
        return jsonify({"error": "set_name required"}), 400

    # Find album by old set name
    album = Album.query.filter_by(
        name=set_name.replace("_", " ").title(),
        is_set_template=True
    ).first()

    if not album:
        return jsonify({"error": f"Set '{set_name}' not found"}), 404

    # Forward to new endpoint
    return generate_batch_from_album(album.id)
```

### Phase 4: Frontend Updates

#### 4.1 Update AlbumsTab to Show Set Templates

```tsx
// web/src/components/AlbumsTab.tsx

const AlbumsTab: React.FC<Props> = ({ isAdmin }) => {
  const [viewMode, setViewMode] = useState<'all' | 'sets' | 'regular'>('all')

  const filteredAlbums = albums.filter(album => {
    if (viewMode === 'sets') return album.is_set_template
    if (viewMode === 'regular') return !album.is_set_template
    return true
  })

  return (
    <div className="albums-tab">
      <div className="view-mode-toggle">
        <button onClick={() => setViewMode('all')}>All Albums</button>
        <button onClick={() => setViewMode('sets')}>Set Templates</button>
        <button onClick={() => setViewMode('regular')}>Regular Albums</button>
      </div>

      {/* For set templates, show batch generation button */}
      {album.is_set_template && isAdmin && (
        <button onClick={() => generateBatch(album.id)}>
          Generate All ({album.template_item_count} items)
        </button>
      )}
    </div>
  )
}
```

#### 4.2 Create Set Template Editor

```tsx
// web/src/components/SetTemplateEditor.tsx

interface SetTemplateEditorProps {
  albumId: number
}

const SetTemplateEditor: React.FC<SetTemplateEditorProps> = ({ albumId }) => {
  const [template, setTemplate] = useState<SetTemplate | null>(null)

  // CRUD operations for template items
  const addTemplateItem = (item: TemplateItem) => { /* ... */ }
  const updateTemplateItem = (index: number, item: TemplateItem) => { /* ... */ }
  const deleteTemplateItem = (index: number) => { /* ... */ }

  return (
    <div className="set-template-editor">
      <h3>Template Configuration</h3>

      <div className="template-settings">
        <input
          value={template.base_prompt}
          onChange={e => setTemplate({...template, base_prompt: e.target.value})}
          placeholder="Base prompt..."
        />
        <input
          value={template.prompt_template}
          onChange={e => setTemplate({...template, prompt_template: e.target.value})}
          placeholder="Prompt template (use {field} placeholders)..."
        />
        {/* More template fields... */}
      </div>

      <div className="template-items">
        <h4>Template Items ({template.items.length})</h4>
        <CSVUpload onUpload={handleCSVUpload} />
        <table>
          <thead>
            <tr>
              {Object.keys(template.items[0] || {}).map(key => (
                <th key={key}>{key}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {template.items.map((item, i) => (
              <tr key={i}>
                {Object.entries(item).map(([key, value]) => (
                  <td key={key}>
                    <input
                      value={value}
                      onChange={e => updateTemplateItem(i, {...item, [key]: e.target.value})}
                    />
                  </td>
                ))}
                <td>
                  <button onClick={() => deleteTemplateItem(i)}>Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
```

### Phase 5: Backward Compatibility Layer

Keep old endpoints working but mark as deprecated:

```python
# server/routes/legacy_sets.py

legacy_sets_bp = Blueprint('legacy_sets', __name__)

@legacy_sets_bp.before_request
def log_deprecated_usage():
    logger.warning(
        f"Deprecated sets API called: {request.path}",
        extra={"endpoint": request.endpoint, "user_agent": request.user_agent.string}
    )

@legacy_sets_bp.route("/api/sets", methods=["GET"])
def list_sets():
    """Legacy endpoint - redirects to albums"""
    return redirect(url_for('albums.list_albums', is_set_template=True))

# Register blueprint
app.register_blueprint(legacy_sets_bp)
```

## Implementation Checklist

### Phase 1: Database Schema ✅
- [ ] Create Alembic migration for new fields
- [ ] Add `is_set_template`, `csv_data`, `base_prompt`, `prompt_template`, `style_suffix`, `example_theme`, `lora_config`
- [ ] Test migration up/down
- [ ] Update `Album.to_dict()` to include new fields

### Phase 2: Data Migration ✅
- [ ] Write migration script `scripts/migrate_sets_to_albums.py`
- [ ] Test migration on dev database
- [ ] Backup production data
- [ ] Run migration in production
- [ ] Verify all sets imported correctly

### Phase 3: Backend API ✅
- [ ] Update `Album` model methods
- [ ] Create `/api/albums/{id}/generate/batch` endpoint
- [ ] Add `/api/albums/{id}/template` CRUD endpoints
- [ ] Deprecate `/api/sets` (redirect to albums)
- [ ] Deprecate `/api/generate/batch` (forward to new endpoint)
- [ ] Update tests for albums API
- [ ] Add tests for set template functionality

### Phase 4: Frontend ✅
- [ ] Update `AlbumsTab` to show set templates
- [ ] Add view mode toggle (all/sets/regular)
- [ ] Create `SetTemplateEditor` component
- [ ] Add CSV upload/download for template items
- [ ] Update batch generation UI to use albums
- [ ] Remove deprecated `GenerateTab` set selection

### Phase 5: Cleanup ✅
- [ ] Remove `load_sets_config()` from `server/api.py`
- [ ] Remove `get_set_config()` from `server/api.py`
- [ ] Remove `load_set_data()` from `server/api.py`
- [ ] Archive CSV files to `sets_archive/` for reference
- [ ] Update documentation
- [ ] Remove `sets.directory` from `config.yaml`

## Testing Strategy

### Unit Tests
```python
# tests/backend/test_set_templates.py

def test_create_set_template_album(client, admin_client):
    """Test creating album with set template"""
    data = {
        "name": "Test Deck",
        "is_set_template": True,
        "csv_data": json.dumps([{"card": "Ace"}, {"card": "King"}]),
        "prompt_template": "A {card} card"
    }
    response = admin_client.post("/api/albums", json=data)
    assert response.status_code == 201
    assert response.json["is_set_template"] == True

def test_generate_batch_from_album(client, admin_client, app):
    """Test batch generation from set template"""
    with app.app_context():
        album = Album(
            name="Test Set",
            is_set_template=True,
            csv_data=json.dumps([{"item": "1"}, {"item": "2"}]),
            prompt_template="Generate {item}"
        )
        db.session.add(album)
        db.session.commit()

        response = admin_client.post(f"/api/albums/{album.id}/generate/batch")
        assert response.status_code == 201
        assert response.json["jobs_count"] == 2
```

### Integration Tests
```python
def test_complete_set_workflow(client, admin_client):
    """Test complete workflow: create → edit → generate → view"""
    # Create set template
    response = admin_client.post("/api/albums", json={...})
    album_id = response.json["id"]

    # Update template
    admin_client.put(f"/api/albums/{album_id}", json={...})

    # Generate batch
    admin_client.post(f"/api/albums/{album_id}/generate/batch")

    # View results
    response = client.get(f"/api/albums/{album_id}")
    assert len(response.json["images"]) > 0
```

## Rollback Plan

If issues arise during migration:

1. **Database rollback:**
   ```bash
   alembic downgrade -1
   ```

2. **Restore legacy endpoints:**
   ```python
   # Re-enable full legacy implementation
   app.config['LEGACY_SETS_ENABLED'] = True
   ```

3. **Data recovery:**
   ```bash
   # CSV files remain unchanged in /mnt/speedy/imagineer/sets/
   # Can always re-read from source
   ```

## Benefits

### For Users
- ✅ Manage set templates through the UI
- ✅ Edit template items without editing CSVs
- ✅ See generated images linked to their source set
- ✅ Use same privacy/sharing controls for sets
- ✅ Apply labeling and training to set images

### For Developers
- ✅ Single source of truth (database)
- ✅ Unified API (no special set logic)
- ✅ Better testability
- ✅ Easier to add features (everything in DB)
- ✅ No file system dependencies

### For System
- ✅ Better scalability (no file I/O for sets)
- ✅ Atomic operations (database transactions)
- ✅ Better audit trail (who created/modified)
- ✅ Easier backups (just database)

## Timeline

- **Week 1:** Phase 1 + 2 (Schema + Migration)
- **Week 2:** Phase 3 (Backend API)
- **Week 3:** Phase 4 (Frontend)
- **Week 4:** Phase 5 (Cleanup) + Testing
- **Week 5:** Production deployment

## Open Questions

1. Should we preserve CSV files after migration?
   - **Recommendation:** Yes, move to `sets_archive/` for reference

2. Should old `/api/sets` endpoint return 410 Gone or redirect?
   - **Recommendation:** Redirect for 6 months, then return 410

3. What about existing batch jobs that reference set names?
   - **Recommendation:** Add `set_name` → `album_id` migration mapping

4. Should we support importing new sets via CSV?
   - **Recommendation:** Yes, create `/api/albums/import-csv` endpoint
