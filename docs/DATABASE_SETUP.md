# Database Setup & Migration Guide

**Last Updated:** 2025-10-28

## Overview

Imagineer uses SQLite for data persistence. This guide covers database initialization, migrations, and troubleshooting.

---

## Quick Start

### First-Time Setup

```bash
# 1. Activate virtual environment
source venv/bin/activate

# 2. Database is created automatically on first run
python server/api.py

# 3. (Optional) Import existing images
python scripts/migrate_to_database.py
```

That's it! The database is automatically created at `instance/imagineer.db` when you start the server.

---

## Database Location

**Path:** `instance/imagineer.db`

**Why instance/?**
- Flask convention for instance-specific data
- Excluded from version control
- Safe for local development

**Important:** Never commit `instance/imagineer.db` to git. It's a binary file that changes frequently.

---

## Schema Overview

### Tables

| Table | Purpose | Records |
|-------|---------|---------|
| `images` | All images with metadata | Many |
| `albums` | Collections of images | Many |
| `album_images` | Many-to-many: albums ↔ images | Many |
| `labels` | AI-generated and manual labels | Many |
| `scrape_jobs` | Web scraping job tracking | Few |
| `training_runs` | LoRA training job tracking | Few |

### Relationships

```
images (1) ──< (many) album_images >── (many) albums
images (1) ──< (many) labels
```

---

## Database Creation

### Automatic Creation

The database is **automatically created** when you start the Flask app:

```python
# server/database.py
def init_database(app):
    """Initialize database and create tables if needed"""
    db.init_app(app)

    with app.app_context():
        db.create_all()  # Creates tables if they don't exist
        logger.info("Database tables created successfully")
```

**When it runs:**
- First time you start `python server/api.py`
- First time you run tests
- Any time `instance/imagineer.db` doesn't exist

**What it creates:**
- All 6 tables with proper schema
- Indexes for performance
- Foreign key constraints

### Manual Creation

If you need to recreate the database:

```bash
# 1. Delete existing database (CAUTION: Deletes all data!)
rm instance/imagineer.db

# 2. Start the server (creates fresh database)
python server/api.py
```

Or use the migration script:

```bash
python scripts/migrate_to_database.py
```

---

## Migration Scripts

### migrate_to_database.py

**Purpose:** Import existing images from `/mnt/speedy/imagineer/outputs/` to database

**What it does:**
1. Scans outputs directory for batch folders
2. Creates album for each batch
3. Imports all images with metadata
4. Creates database records for each image

**Usage:**
```bash
python scripts/migrate_to_database.py
```

**When to run:**
- After setting up fresh database
- When you have existing images to import
- After cleaning database (not recommended)

**Safe to run multiple times:** Yes, it skips images already in database

---

### migrate_add_training_source.py

**Purpose:** Add `is_training_source` column to albums table

**What it does:**
- Adds new column to existing albums table
- Sets default value to False
- Safe to run on databases that already have the column

**Usage:**
```bash
python scripts/migrate_add_training_source.py
```

**When to run:**
- If upgrading from older schema (pre-Oct 2025)
- If you see error: "no such column: is_training_source"

**Safe to run multiple times:** Yes, checks if column exists first

---

## Git Ignore Status

### Problem: "Dirty" Database in Git

**Symptom:**
```bash
$ git status
Changes not staged for commit:
  modified:   instance/imagineer.db
```

**Root Cause:**
- Database file was committed to git at some point
- Every time app runs, database changes
- Git sees these changes as "modifications"

**Why this is wrong:**
- SQLite databases are binary files
- They change on every query/transaction
- Not suitable for version control
- Causes constant git noise

### Solution: Untrack Database

**Step 1: Add to .gitignore**

Already done! The `.gitignore` should include:
```gitignore
# Database files
instance/
*.db
*.db-journal
*.db-shm
*.db-wal
```

**Step 2: Remove from git tracking**

```bash
# Stop tracking the file (but keep local copy)
git rm --cached instance/imagineer.db

# Commit the change
git commit -m "fix: Remove SQLite database from version control

Database files should not be in git:
- Binary format not suitable for version control
- Changes on every query/transaction
- Causes constant dirty git status

Database is now:
- ✅ Excluded via .gitignore
- ✅ Created automatically on first run
- ✅ Local to each environment"

# Push the change
git push origin develop
```

**Step 3: Verify**

```bash
# Should not show database anymore
git status

# Database still exists locally
ls -la instance/imagineer.db  # ✅ File exists

# But not tracked by git
git ls-files | grep imagineer.db  # ❌ No output (good!)
```

---

## Database Schema Migrations

### Current Approach: Manual Scripts

**Status:** No formal migration system (Alembic) yet

**How schema changes work:**
1. Update model definitions in `server/database.py`
2. Write migration script if needed
3. Run script to update existing databases
4. New databases get correct schema automatically

**Example workflow:**

```python
# 1. Add new column to model (server/database.py)
class Album(db.Model):
    # ... existing columns ...
    is_featured = db.Column(db.Boolean, default=False)  # NEW COLUMN

# 2. Create migration script (scripts/migrate_add_featured.py)
def migrate_add_featured():
    with db.engine.connect() as conn:
        conn.execute(db.text("ALTER TABLE albums ADD COLUMN is_featured BOOLEAN DEFAULT 0"))
        conn.commit()

# 3. Run migration
python scripts/migrate_add_featured.py

# 4. New databases automatically have the column
```

### Future: Alembic Migrations

**Planned enhancement:** Add Alembic for proper migration management

**Benefits:**
- Version-controlled schema changes
- Automatic upgrade/downgrade
- Better tracking of schema history
- Industry standard tool

**Setup (when implemented):**
```bash
# Initialize Alembic
alembic init migrations

# Create migration
alembic revision --autogenerate -m "Add featured column"

# Apply migration
alembic upgrade head

# Rollback if needed
alembic downgrade -1
```

---

## Troubleshooting

### Problem: "no such table: images"

**Cause:** Database doesn't exist or tables not created

**Solution:**
```bash
# Start the server (creates tables automatically)
python server/api.py
```

Or manually:
```python
from server.api import app
from server.database import db

with app.app_context():
    db.create_all()
```

---

### Problem: "no such column: is_training_source"

**Cause:** Old database schema, missing new column

**Solution:**
```bash
python scripts/migrate_add_training_source.py
```

---

### Problem: "database is locked"

**Cause:** Another process has database open

**Solution:**
```bash
# 1. Find process
lsof instance/imagineer.db

# 2. Stop the server/process
# Kill the process or stop the dev server

# 3. Try again
python server/api.py
```

---

### Problem: Corrupt database

**Symptoms:**
- "database disk image is malformed"
- "file is not a database"
- Random errors

**Solution:**

**Option 1: Recreate database (CAUTION: Loses all data)**
```bash
rm instance/imagineer.db
python server/api.py
python scripts/migrate_to_database.py  # Re-import images if needed
```

**Option 2: Attempt repair**
```bash
# Dump to SQL
sqlite3 instance/imagineer.db .dump > backup.sql

# Remove corrupt database
rm instance/imagineer.db

# Restore from dump
sqlite3 instance/imagineer.db < backup.sql
```

---

### Problem: "dirty" git status after fix

**Cause:** Database still tracked despite .gitignore

**Solution:**
```bash
# Check if still tracked
git ls-files | grep imagineer.db

# If it appears, untrack it
git rm --cached instance/imagineer.db
git commit -m "fix: Untrack database file"
git push origin develop
```

---

## Testing

### Test Database

Tests use the same database by default: `instance/imagineer.db`

**Considerations:**
- Tests may modify database
- Test data pollutes development data
- Parallel tests conflict

**Best practice:** Use separate test database

```python
# tests/conftest.py
@pytest.fixture(scope="session")
def app():
    """Create test app with separate database"""
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///test.db"
    app.config["TESTING"] = True

    db.init_app(app)

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

    # Clean up
    Path("test.db").unlink(missing_ok=True)
```

---

## Backup & Restore

### Backup

**SQLite is a single file**, so backup is simple:

```bash
# Copy the file
cp instance/imagineer.db instance/imagineer.db.backup

# Or with timestamp
cp instance/imagineer.db "backups/imagineer-$(date +%Y%m%d-%H%M%S).db"
```

**Automated backup:**
```bash
# Add to crontab for daily backups
0 2 * * * cd /home/jdubz/Development/imagineer && cp instance/imagineer.db "backups/imagineer-$(date +\%Y\%m\%d).db"
```

### Restore

```bash
# Stop server first!
cp instance/imagineer.db.backup instance/imagineer.db

# Or specific backup
cp backups/imagineer-20251028.db instance/imagineer.db

# Restart server
python server/api.py
```

---

## Production Considerations

### Database Location

**Development:** `instance/imagineer.db` (local)

**Production:** Should be:
- On persistent storage (not tmpfs)
- Backed up regularly
- Monitored for size/corruption

**Recommended production path:**
```
/mnt/speedy/imagineer/database/imagineer.db
```

### Performance

**SQLite limits:**
- Single writer at a time
- Good for low-concurrency workloads
- Max database size: ~281 TB (not a concern)
- Max row count: 2^64 (not a concern)

**When to migrate to PostgreSQL:**
- Multiple concurrent writers
- High traffic (>1000 req/sec)
- Complex queries slow down
- Need replication/clustering

**Current scale:** SQLite is perfect
- Single server
- Low traffic (you + friends)
- Simple queries
- No need for PostgreSQL complexity

---

## Schema Documentation

### Images Table

```sql
CREATE TABLE images (
    id INTEGER PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL UNIQUE,
    width INTEGER,
    height INTEGER,
    file_size INTEGER,
    is_nsfw BOOLEAN DEFAULT 0,
    is_public BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Indexes for performance
    INDEX idx_images_is_public (is_public),
    INDEX idx_images_is_nsfw (is_nsfw),
    INDEX idx_images_created_at (created_at)
);
```

### Albums Table

```sql
CREATE TABLE albums (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    album_type VARCHAR(50) DEFAULT 'batch',
    is_public BOOLEAN DEFAULT 1,
    is_training_source BOOLEAN DEFAULT 0,
    created_by VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_albums_is_public (is_public),
    INDEX idx_albums_album_type (album_type)
);
```

### Album Images (Junction Table)

```sql
CREATE TABLE album_images (
    album_id INTEGER NOT NULL,
    image_id INTEGER NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    added_by VARCHAR(255),
    sort_order INTEGER DEFAULT 0,
    PRIMARY KEY (album_id, image_id),
    FOREIGN KEY (album_id) REFERENCES albums(id) ON DELETE CASCADE,
    FOREIGN KEY (image_id) REFERENCES images(id) ON DELETE CASCADE
);
```

### Labels Table

```sql
CREATE TABLE labels (
    id INTEGER PRIMARY KEY,
    image_id INTEGER NOT NULL,
    label_text TEXT NOT NULL,
    label_type VARCHAR(20),  -- caption, tag, category
    source_model VARCHAR(50),  -- claude-3-5-sonnet, manual, scraper
    confidence FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (image_id) REFERENCES images(id) ON DELETE CASCADE,
    INDEX idx_labels_image_id (image_id),
    INDEX idx_labels_label_type (label_type)
);
```

### Training Runs Table

```sql
CREATE TABLE training_runs (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    dataset_path VARCHAR(500) NOT NULL,
    output_path VARCHAR(500) NOT NULL,
    training_config TEXT,  -- JSON
    status VARCHAR(50) DEFAULT 'pending',
    progress INTEGER DEFAULT 0,
    final_checkpoint VARCHAR(500),
    training_loss FLOAT,
    validation_loss FLOAT,
    error_message TEXT,
    last_error_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    INDEX idx_training_runs_status (status)
);
```

### Scrape Jobs Table

```sql
CREATE TABLE scrape_jobs (
    id INTEGER PRIMARY KEY,
    source_url VARCHAR(500) NOT NULL,
    album_name VARCHAR(100) NOT NULL,
    scrape_config TEXT,  -- JSON
    status VARCHAR(50) DEFAULT 'pending',
    progress INTEGER DEFAULT 0,
    images_scraped INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_by VARCHAR(255),
    INDEX idx_scrape_jobs_status (status)
);
```

---

## Summary

### Key Points

1. **Database is auto-created** - No manual setup needed
2. **SQLite is perfect** - No need for PostgreSQL at current scale
3. **Migration scripts exist** - For schema updates and data import
4. **Not in git** - Database should be excluded from version control
5. **Simple backup** - Just copy the file

### Quick Commands

```bash
# Start server (creates database automatically)
python server/api.py

# Import existing images
python scripts/migrate_to_database.py

# Update schema (if needed)
python scripts/migrate_add_training_source.py

# Backup database
cp instance/imagineer.db backups/$(date +%Y%m%d).db

# Remove from git tracking
git rm --cached instance/imagineer.db
```

---

**Status:** SQLite working perfectly, no issues with current approach
**Future:** Consider Alembic for version-controlled migrations
**Scale:** Current setup good for 100k+ images and 1000+ albums
