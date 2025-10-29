# Imagineer - Revised Comprehensive Improvement Plan

**Project:** Imagineer AI Image Generation & Training Platform
**Audit Date:** 2025-10-26
**Project Phase:** Active Development → Multi-User Platform with Training Pipeline
**Infrastructure:** Local RTX 3080 server + Firebase hosting + Cloudflare tunnel

---

## Executive Summary

This revised plan aligns with your actual vision: **A complete AI image generation and model training platform** for you and friends to collaboratively build datasets, train models, and generate images. The focus shifts from generic improvements to building the specific features needed for your training workflow.

### Your Actual Goals

1. **Public Gallery:** Anyone can view images/albums/LoRAs/labels (no auth required)
2. **Admin-Only Editing:** Only 2 admins can upload, delete, create, train (contact@joshwentworth.com, jessica.castaldi@gmail.com)
3. **Album System:** Organize images into collections for viewing and training
4. **AI Labeling:** Use Claude vision to caption images for training
5. **Web Scraping:** Integrate existing training-data project to collect datasets
6. **Training Pipeline:** UI-driven LoRA training from albums, with progress monitoring
7. **NSFW Support:** Blur 18+ content with simple click-through

### Critical Context

**Hardware:**
- RTX 3080 10GB VRAM (perfect for SD 1.5 + LoRA training)
- 64GB RAM (excellent for batch processing)
- 2x500GB drives (NVMe + SSD)
- Always-on home server (Cloudflare tunnel for external access)

**Existing Assets:**
- ✅ Functional web scraper with AI captioning (`/home/jdubz/Development/training-data/`)
- ✅ Google OAuth working (just implemented)
- ✅ LoRA training script ready (`examples/train_lora.py`)
- ✅ Generation system mature and stable
- ❌ No database (pure filesystem currently)
- ❌ No albums, labeling, or training integration

---

## Architectural Decisions

### Database: SQLite (Perfect for Your Scale)

**Rationale:**
- Low traffic (you + friends, not thousands of users)
- Single server deployment
- No need for PostgreSQL complexity
- Easy backups (single file)
- Excellent Python integration

**Schema Overview:**
```sql
-- Core tables
images          -- All images with metadata
labels          -- AI-generated and manual labels
albums          -- Collections (generated sets, training data, custom)
album_images    -- Many-to-many: images ↔ albums
users           -- Just 2 admins (replace users.json)
scrape_jobs     -- Web scraping job tracking
training_runs   -- LoRA training job tracking
```

### Authentication: Simplified Public + Admin

**Remove:** viewer/editor roles (unnecessary complexity)
**Keep:** Google OAuth for 2 admins only
**Add:** Public read access for all GET endpoints

```python
# Two admins only
ADMIN_EMAILS = [
    "contact@joshwentworth.com",
    "jessica.castaldi@gmail.com"
]

# Public viewing (no auth)
GET /api/images
GET /api/albums
GET /api/loras
GET /api/batches

# Admin only (OAuth required)
POST /api/images/upload
DELETE /api/images/{id}
POST /api/training/start
POST /api/scrape/start
```

### Job Queue: Celery + Redis (Required for Long-Running Jobs)

**Why:**
- Web scraping can run for hours
- Training runs take 30-60 minutes
- Need proper cancellation support
- Queue must survive server restarts

**Jobs:**
- Image generation (existing)
- Batch generation (existing)
- **NEW:** Web scraping jobs
- **NEW:** Training jobs
- **NEW:** Batch AI labeling
- **NEW:** Image upscaling (future)

### Image Organization Strategy

**Filesystem:**
```
/mnt/speedy/imagineer/outputs/
├── batches/
│   └── {batch_id}/              # Generated images (existing)
│       ├── image.png
│       └── image.json
├── uploads/
│   └── {upload_id}/             # Manual uploads (new)
│       └── *.png
├── scraped/
│   └── {scrape_job_id}/         # Web scraping results (new)
│       ├── image_0001.jpg
│       └── image_0001.txt       # SD 1.5 caption format
└── thumbnails/
    └── {image_id}.webp          # Auto-generated 300px thumbnails (new)
```

**Database:**
- All images registered in `images` table
- Path stored, organized by source (batch/upload/scrape)
- Albums are virtual collections (DB records + junction table)
- Images can belong to multiple albums

---

## Phased Implementation Roadmap

### Phase 1: Foundation & Security (Week 1, 20-25 hours)

**Goal:** Fix critical issues, add database, simplify auth, enable public viewing

#### 1.1 Critical Security Fixes (6 hours)

**Issues from previous audit that are CRITICAL:**

1. **Remove hardcoded secrets** (1 hour)
```python
# server/auth.py - Force FLASK_SECRET_KEY in production
def get_secret_key() -> str:
    secret = os.environ.get("FLASK_SECRET_KEY")
    if not secret:
        if os.environ.get("FLASK_ENV") == "production":
            raise RuntimeError("FLASK_SECRET_KEY must be set")
        # Dev only
        import secrets
        secret = secrets.token_hex(32)
        logger.warning(f"Using generated dev key")
    return secret

app.config["SECRET_KEY"] = get_secret_key()
```

2. **Remove PasswordGate** (1 hour)
```bash
# Delete legacy password authentication
rm web/src/components/PasswordGate.jsx
rm web/src/styles/PasswordGate.css

# Update App.jsx to remove wrapper
# Remove VITE_APP_PASSWORD from .env files
```

3. **Fix CORS for production** (1 hour)
```python
# server/api.py
ALLOWED_ORIGINS = os.environ.get('ALLOWED_ORIGINS', '').split(',')
if not ALLOWED_ORIGINS or ALLOWED_ORIGINS == ['']:
    ALLOWED_ORIGINS = [
        'http://localhost:3000',
        'http://localhost:5173',
        'https://imagineer.joshwentworth.com'
    ]

CORS(app,
     resources={r"/api/*": {"origins": ALLOWED_ORIGINS}},
     supports_credentials=True)
```

4. **Add security headers** (2 hours)
```python
# requirements.txt
flask-talisman>=1.1.0

# server/api.py
from flask_talisman import Talisman

if os.environ.get('FLASK_ENV') == 'production':
    Talisman(app,
        force_https=True,
        content_security_policy={
            'default-src': "'self'",
            'img-src': ["'self'", "data:", "*.googleusercontent.com"],
            'script-src': ["'self'", "'unsafe-inline'", "accounts.google.com"],
            'style-src': ["'self'", "'unsafe-inline'"]
        })
```

5. **Add structured logging** (1 hour)
```python
# server/logging_config.py (NEW FILE)
import logging
from logging.handlers import RotatingFileHandler

def configure_logging():
    os.makedirs('logs', exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            RotatingFileHandler('logs/imagineer.log', maxBytes=10485760, backupCount=5),
            logging.StreamHandler()
        ]
    )

    return logging.getLogger(__name__)
```

#### 1.2 Database Setup (8 hours)

**Create SQLite schema:**

```python
# server/database.py (NEW FILE)
"""Database models for Imagineer"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import hashlib
from pathlib import Path

db = SQLAlchemy()

class Image(db.Model):
    """Image records with metadata"""
    __tablename__ = 'images'

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    path = db.Column(db.String(500), nullable=False, unique=True)

    # Source tracking
    source_type = db.Column(db.String(20), nullable=False)  # 'batch', 'upload', 'scraped'
    source_id = db.Column(db.String(100))  # batch_id, upload_id, or scrape_job_id

    # Image properties
    width = db.Column(db.Integer)
    height = db.Column(db.Integer)
    file_size = db.Column(db.Integer)
    checksum = db.Column(db.String(64))  # SHA256

    # Generation metadata (if generated)
    prompt = db.Column(db.Text)
    generation_params = db.Column(db.JSON)

    # NSFW classification
    nsfw_flag = db.Column(db.Boolean, default=False, index=True)
    nsfw_level = db.Column(db.String(20))  # SAFE, SUGGESTIVE, ADULT, EXPLICIT

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    labels = db.relationship('Label', backref='image', cascade='all, delete-orphan')
    album_associations = db.relationship('AlbumImage', backref='image', cascade='all, delete-orphan')

    def to_dict(self, include_labels=False):
        data = {
            'id': self.id,
            'filename': self.filename,
            'path': self.path,
            'url': f'/api/outputs/{self.path.replace("/mnt/speedy/imagineer/outputs/", "")}',
            'thumbnail_url': f'/api/thumbnails/{self.id}',
            'source_type': self.source_type,
            'source_id': self.source_id,
            'width': self.width,
            'height': self.height,
            'file_size': self.file_size,
            'nsfw_flag': self.nsfw_flag,
            'nsfw_level': self.nsfw_level,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'prompt': self.prompt,
            'generation_params': self.generation_params
        }

        if include_labels:
            data['labels'] = [label.to_dict() for label in self.labels]

        return data

class Label(db.Model):
    """Image labels/captions"""
    __tablename__ = 'labels'

    id = db.Column(db.Integer, primary_key=True)
    image_id = db.Column(db.Integer, db.ForeignKey('images.id'), nullable=False, index=True)

    label_text = db.Column(db.Text, nullable=False)
    confidence = db.Column(db.Float)
    label_type = db.Column(db.String(20))  # 'caption', 'tag', 'category'
    source = db.Column(db.String(20))  # 'claude', 'manual', 'scraper'

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(255))  # Admin email

    def to_dict(self):
        return {
            'id': self.id,
            'image_id': self.image_id,
            'text': self.label_text,
            'confidence': self.confidence,
            'type': self.label_type,
            'source': self.source,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by': self.created_by
        }

class Album(db.Model):
    """Album/collection of images"""
    __tablename__ = 'albums'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True, index=True)
    description = db.Column(db.Text)

    # Cover image
    cover_image_id = db.Column(db.Integer, db.ForeignKey('images.id'))
    cover_image = db.relationship('Image', foreign_keys=[cover_image_id])

    # Training flag
    is_training_source = db.Column(db.Boolean, default=False, index=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_by = db.Column(db.String(255))  # Admin email

    # Relationships
    image_associations = db.relationship('AlbumImage', backref='album', cascade='all, delete-orphan')

    @property
    def image_count(self):
        return len(self.image_associations)

    def to_dict(self, include_images=False):
        data = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'cover_image_id': self.cover_image_id,
            'cover_image_url': f'/api/thumbnails/{self.cover_image_id}' if self.cover_image_id else None,
            'is_training_source': self.is_training_source,
            'image_count': self.image_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by': self.created_by
        }

        if include_images:
            data['images'] = [assoc.image.to_dict() for assoc in self.image_associations]

        return data

class AlbumImage(db.Model):
    """Many-to-many: Albums ↔ Images"""
    __tablename__ = 'album_images'

    album_id = db.Column(db.Integer, db.ForeignKey('albums.id'), primary_key=True)
    image_id = db.Column(db.Integer, db.ForeignKey('images.id'), primary_key=True)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    added_by = db.Column(db.String(255))  # Admin email

class ScrapeJob(db.Model):
    """Web scraping job tracking"""
    __tablename__ = 'scrape_jobs'

    id = db.Column(db.Integer, primary_key=True)
    celery_task_id = db.Column(db.String(36), unique=True, index=True)

    # Job configuration
    url = db.Column(db.String(500), nullable=False)
    album_name = db.Column(db.String(100), nullable=False)
    depth = db.Column(db.Integer, default=3)

    # Status
    status = db.Column(db.String(20), default='pending', index=True)  # pending, running, completed, failed
    progress_message = db.Column(db.Text)

    # Results
    images_discovered = db.Column(db.Integer, default=0)
    images_downloaded = db.Column(db.Integer, default=0)
    images_filtered = db.Column(db.Integer, default=0)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    created_by = db.Column(db.String(255))  # Admin email

    def to_dict(self):
        return {
            'id': self.id,
            'task_id': self.celery_task_id,
            'url': self.url,
            'album_name': self.album_name,
            'status': self.status,
            'progress': self.progress_message,
            'stats': {
                'discovered': self.images_discovered,
                'downloaded': self.images_downloaded,
                'filtered': self.images_filtered
            },
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_by': self.created_by
        }

class TrainingRun(db.Model):
    """LoRA training job tracking"""
    __tablename__ = 'training_runs'

    id = db.Column(db.Integer, primary_key=True)
    celery_task_id = db.Column(db.String(36), unique=True, index=True)

    name = db.Column(db.String(100), nullable=False)
    album_ids = db.Column(db.JSON)  # List of album IDs used for training

    # Configuration
    config = db.Column(db.JSON)  # Training hyperparameters

    # Status
    status = db.Column(db.String(20), default='pending', index=True)
    progress_percentage = db.Column(db.Float, default=0)
    current_step = db.Column(db.Integer, default=0)
    total_steps = db.Column(db.Integer)

    # Results
    output_lora_path = db.Column(db.String(500))
    training_logs = db.Column(db.Text)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    created_by = db.Column(db.String(255))  # Admin email

    def to_dict(self):
        return {
            'id': self.id,
            'task_id': self.celery_task_id,
            'name': self.name,
            'album_ids': self.album_ids,
            'config': self.config,
            'status': self.status,
            'progress': self.progress_percentage,
            'current_step': self.current_step,
            'total_steps': self.total_steps,
            'output_lora_path': self.output_lora_path,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_by': self.created_by
        }

# server/api.py - Initialize database
from server.database import db

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///imagineer.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()
```

**Migration script for existing data:**

```python
# scripts/migrate_to_database.py (NEW FILE)
"""Migrate existing filesystem data to database"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.api import app
from server.database import db, Image, Album, AlbumImage
import json
from datetime import datetime

def migrate_existing_batches():
    """Import all existing generated images"""
    output_dir = Path('/mnt/speedy/imagineer/outputs')

    with app.app_context():
        for batch_dir in output_dir.iterdir():
            if not batch_dir.is_dir():
                continue

            batch_id = batch_dir.name

            # Create album for this batch
            album = Album(
                name=f"Generated: {batch_id}",
                description=f"Batch generation from {batch_id}",
                is_training_source=False,
                created_by='migration'
            )
            db.session.add(album)

            # Import all images in batch
            for image_file in batch_dir.glob('*.png'):
                metadata_file = image_file.with_suffix('.json')

                # Load metadata if exists
                metadata = {}
                if metadata_file.exists():
                    with open(metadata_file) as f:
                        metadata = json.load(f)

                # Create image record
                image = Image(
                    filename=image_file.name,
                    path=str(image_file),
                    source_type='batch',
                    source_id=batch_id,
                    width=metadata.get('width'),
                    height=metadata.get('height'),
                    file_size=image_file.stat().st_size,
                    prompt=metadata.get('prompt'),
                    generation_params=metadata,
                    created_at=datetime.fromtimestamp(image_file.stat().st_mtime)
                )
                db.session.add(image)
                db.session.flush()  # Get image.id

                # Associate with album
                assoc = AlbumImage(
                    album_id=album.id,
                    image_id=image.id,
                    added_by='migration'
                )
                db.session.add(assoc)

                print(f"Imported: {image_file.name}")

            db.session.commit()
            print(f"Completed batch: {batch_id}")

if __name__ == '__main__':
    migrate_existing_batches()
    print("Migration complete!")
```

#### 1.3 Simplified Auth (6 hours)

**Update auth to public + admin only:**

```python
# server/auth.py - Simplify to admin-only

ADMIN_EMAILS = [
    "contact@joshwentworth.com",
    "jessica.castaldi@gmail.com"
]

def is_admin():
    """Check if current user is admin"""
    if not current_user.is_authenticated:
        return False
    return current_user.email in ADMIN_EMAILS

def require_admin(f):
    """Decorator to require admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({"error": "Authentication required"}), 401

        if not is_admin():
            return jsonify({"error": "Admin access required"}), 403

        return f(*args, **kwargs)

    return decorated_function

# Remove @require_auth decorator - no longer needed
# Remove viewer/editor roles
# Keep only @require_admin decorator
```

**Update API endpoints:**

```python
# server/api.py - Public GET, Admin POST/PUT/DELETE

# Public endpoints (no auth)
@app.route("/api/images", methods=["GET"])
def list_images():
    """Anyone can view images"""
    pass

@app.route("/api/albums", methods=["GET"])
def list_albums():
    """Anyone can view albums"""
    pass

@app.route("/api/albums/<int:album_id>", methods=["GET"])
def get_album(album_id):
    """Anyone can view album details"""
    pass

# Admin-only endpoints
@app.route("/api/albums", methods=["POST"])
@require_admin
def create_album():
    """Only admins can create albums"""
    pass

@app.route("/api/albums/<int:album_id>", methods=["DELETE"])
@require_admin
def delete_album(album_id):
    """Only admins can delete albums"""
    pass

@app.route("/api/images/upload", methods=["POST"])
@require_admin
def upload_images():
    """Only admins can upload images"""
    pass
```

**Update frontend:**

```javascript
// web/src/components/AuthButton.jsx
// Simplify to show "Admin" badge or "Public Viewer"

function AuthButton() {
  const [user, setUser] = useState(null)

  useEffect(() => {
    fetch('/api/auth/me', { credentials: 'include' })
      .then(res => res.json())
      .then(data => {
        if (data.authenticated) {
          setUser(data.user)
        }
      })
  }, [])

  if (user) {
    return (
      <div className="auth-button">
        <span className="admin-badge">Admin: {user.email}</span>
        <button onClick={() => window.location.href = '/auth/logout'}>
          Logout
        </button>
      </div>
    )
  }

  return (
    <div className="auth-button">
      <span className="viewer-badge">Public Viewer</span>
      <button onClick={() => window.location.href = '/auth/login'}>
        Admin Login
      </button>
    </div>
  )
}
```

**Phase 1 Deliverables:**
- ✅ Critical security vulnerabilities fixed
- ✅ SQLite database with full schema
- ✅ Existing images migrated to database
- ✅ Auth simplified (public + admin only)
- ✅ Public viewing enabled
- ✅ Structured logging in place

---

### Phase 2: Album System & Image Management (Week 2, 20-25 hours)

**Goal:** Build album UI, import images, organize collections

#### 2.1 Album API Endpoints (8 hours)

```python
# server/routes/albums.py (NEW FILE)
"""Album management endpoints"""

from flask import Blueprint, request, jsonify
from server.database import db, Album, Image, AlbumImage
from server.auth import require_admin, current_user, is_admin
from datetime import datetime

albums_bp = Blueprint('albums', __name__, url_prefix='/api/albums')

@albums_bp.route("", methods=["GET"])
def list_albums():
    """List all albums (public)"""
    albums = Album.query.order_by(Album.created_at.desc()).all()
    return jsonify({
        'albums': [album.to_dict() for album in albums]
    })

@albums_bp.route("/<int:album_id>", methods=["GET"])
def get_album(album_id):
    """Get album details with images (public)"""
    album = Album.query.get_or_404(album_id)
    return jsonify(album.to_dict(include_images=True))

@albums_bp.route("", methods=["POST"])
@require_admin
def create_album():
    """Create new album (admin only)"""
    data = request.json

    album = Album(
        name=data['name'],
        description=data.get('description', ''),
        is_training_source=data.get('is_training_source', False),
        created_by=current_user.email
    )

    db.session.add(album)
    db.session.commit()

    return jsonify(album.to_dict()), 201

@albums_bp.route("/<int:album_id>", methods=["PUT"])
@require_admin
def update_album(album_id):
    """Update album (admin only)"""
    album = Album.query.get_or_404(album_id)
    data = request.json

    if 'name' in data:
        album.name = data['name']
    if 'description' in data:
        album.description = data['description']
    if 'is_training_source' in data:
        album.is_training_source = data['is_training_source']
    if 'cover_image_id' in data:
        album.cover_image_id = data['cover_image_id']

    db.session.commit()

    return jsonify(album.to_dict())

@albums_bp.route("/<int:album_id>", methods=["DELETE"])
@require_admin
def delete_album(album_id):
    """Delete album (admin only)"""
    album = Album.query.get_or_404(album_id)

    db.session.delete(album)
    db.session.commit()

    return jsonify({'success': True})

@albums_bp.route("/<int:album_id>/images", methods=["POST"])
@require_admin
def add_images_to_album(album_id):
    """Add images to album (admin only)"""
    album = Album.query.get_or_404(album_id)
    data = request.json

    image_ids = data.get('image_ids', [])

    for image_id in image_ids:
        # Check if already in album
        existing = AlbumImage.query.filter_by(
            album_id=album_id,
            image_id=image_id
        ).first()

        if not existing:
            assoc = AlbumImage(
                album_id=album_id,
                image_id=image_id,
                added_by=current_user.email
            )
            db.session.add(assoc)

    db.session.commit()

    return jsonify({'success': True, 'added': len(image_ids)})

@albums_bp.route("/<int:album_id>/images/<int:image_id>", methods=["DELETE"])
@require_admin
def remove_image_from_album(album_id, image_id):
    """Remove image from album (admin only)"""
    assoc = AlbumImage.query.filter_by(
        album_id=album_id,
        image_id=image_id
    ).first_or_404()

    db.session.delete(assoc)
    db.session.commit()

    return jsonify({'success': True})

# server/api.py - Register blueprint
from server.routes.albums import albums_bp
app.register_blueprint(albums_bp)
```

#### 2.2 Image API Endpoints (6 hours)

```python
# server/routes/images.py (NEW FILE)
"""Image management endpoints"""

from flask import Blueprint, request, jsonify, send_file
from server.database import db, Image, Label
from server.auth import require_admin, current_user
from werkzeug.utils import secure_filename
from PIL import Image as PILImage
import hashlib
from pathlib import Path
import io

images_bp = Blueprint('images', __name__, url_prefix='/api/images')

@images_bp.route("", methods=["GET"])
def list_images():
    """List all images (public, with pagination)"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    nsfw_filter = request.args.get('nsfw', 'blur')  # 'hide', 'blur', 'show'

    query = Image.query

    # Filter NSFW if requested
    if nsfw_filter == 'hide':
        query = query.filter_by(nsfw_flag=False)

    # Order by newest first
    query = query.order_by(Image.created_at.desc())

    # Paginate
    pagination = query.paginate(page=page, per_page=per_page)

    return jsonify({
        'images': [img.to_dict() for img in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages
    })

@images_bp.route("/<int:image_id>", methods=["GET"])
def get_image(image_id):
    """Get image details (public)"""
    image = Image.query.get_or_404(image_id)
    return jsonify(image.to_dict(include_labels=True))

@images_bp.route("/upload", methods=["POST"])
@require_admin
def upload_images():
    """Upload images (admin only)"""
    if 'files' not in request.files:
        return jsonify({'error': 'No files provided'}), 400

    files = request.files.getlist('files')
    album_id = request.form.get('album_id', type=int)

    # Create upload directory
    from datetime import datetime
    upload_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    upload_dir = Path(f'/mnt/speedy/imagineer/outputs/uploads/{upload_id}')
    upload_dir.mkdir(parents=True, exist_ok=True)

    uploaded_images = []

    for file in files:
        if file.filename == '':
            continue

        # Save file
        filename = secure_filename(file.filename)
        filepath = upload_dir / filename
        file.save(filepath)

        # Get image dimensions
        with PILImage.open(filepath) as img:
            width, height = img.size

        # Calculate checksum
        sha256 = hashlib.sha256()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        checksum = sha256.hexdigest()

        # Create database record
        image = Image(
            filename=filename,
            path=str(filepath),
            source_type='upload',
            source_id=upload_id,
            width=width,
            height=height,
            file_size=filepath.stat().st_size,
            checksum=checksum
        )

        db.session.add(image)
        db.session.flush()  # Get image.id

        # Add to album if specified
        if album_id:
            from server.database import AlbumImage
            assoc = AlbumImage(
                album_id=album_id,
                image_id=image.id,
                added_by=current_user.email
            )
            db.session.add(assoc)

        uploaded_images.append(image.to_dict())

    db.session.commit()

    return jsonify({
        'success': True,
        'uploaded': len(uploaded_images),
        'images': uploaded_images
    }), 201

@images_bp.route("/<int:image_id>", methods=["DELETE"])
@require_admin
def delete_image(image_id):
    """Delete image (admin only)"""
    image = Image.query.get_or_404(image_id)

    # Delete file from filesystem
    filepath = Path(image.path)
    if filepath.exists():
        filepath.unlink()

        # Also delete metadata JSON if exists
        json_path = filepath.with_suffix('.json')
        if json_path.exists():
            json_path.unlink()

    # Delete from database (cascade deletes labels and album associations)
    db.session.delete(image)
    db.session.commit()

    return jsonify({'success': True})

@images_bp.route("/<int:image_id>/labels", methods=["POST"])
@require_admin
def add_label(image_id):
    """Add label to image (admin only)"""
    image = Image.query.get_or_404(image_id)
    data = request.json

    label = Label(
        image_id=image.id,
        label_text=data['text'],
        confidence=data.get('confidence'),
        label_type=data.get('type', 'tag'),
        source=data.get('source', 'manual'),
        created_by=current_user.email
    )

    db.session.add(label)
    db.session.commit()

    return jsonify(label.to_dict()), 201

@images_bp.route("/<int:image_id>/labels/<int:label_id>", methods=["DELETE"])
@require_admin
def delete_label(image_id, label_id):
    """Delete label (admin only)"""
    label = Label.query.filter_by(id=label_id, image_id=image_id).first_or_404()

    db.session.delete(label)
    db.session.commit()

    return jsonify({'success': True})

# Thumbnail generation endpoint
@images_bp.route("/<int:image_id>/thumbnail", methods=["GET"])
def get_thumbnail(image_id):
    """Get image thumbnail (300px, public)"""
    image = Image.query.get_or_404(image_id)

    # Check for cached thumbnail
    thumbnail_dir = Path('/mnt/speedy/imagineer/outputs/thumbnails')
    thumbnail_dir.mkdir(exist_ok=True)
    thumbnail_path = thumbnail_dir / f"{image_id}.webp"

    if not thumbnail_path.exists():
        # Generate thumbnail
        with PILImage.open(image.path) as img:
            img.thumbnail((300, 300))
            img.save(thumbnail_path, 'WEBP', quality=85)

    return send_file(thumbnail_path, mimetype='image/webp')

# server/api.py - Register blueprint
from server.routes.images import images_bp
app.register_blueprint(images_bp)
```

#### 2.3 Frontend Album UI (6-8 hours)

```javascript
// web/src/components/AlbumsTab.jsx (NEW FILE)
import React, { useState, useEffect } from 'react'
import '../styles/AlbumsTab.css'

function AlbumsTab({ isAdmin }) {
  const [albums, setAlbums] = useState([])
  const [selectedAlbum, setSelectedAlbum] = useState(null)
  const [showCreateDialog, setShowCreateDialog] = useState(false)

  useEffect(() => {
    fetchAlbums()
  }, [])

  const fetchAlbums = async () => {
    const response = await fetch('/api/albums')
    const data = await response.json()
    setAlbums(data.albums)
  }

  const selectAlbum = async (albumId) => {
    const response = await fetch(`/api/albums/${albumId}`)
    const data = await response.json()
    setSelectedAlbum(data)
  }

  const createAlbum = async (name, description) => {
    const response = await fetch('/api/albums', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ name, description })
    })

    if (response.ok) {
      fetchAlbums()
      setShowCreateDialog(false)
    }
  }

  if (selectedAlbum) {
    return (
      <AlbumDetailView
        album={selectedAlbum}
        onBack={() => setSelectedAlbum(null)}
        isAdmin={isAdmin}
      />
    )
  }

  return (
    <div className="albums-tab">
      <div className="albums-header">
        <h2>Albums</h2>
        {isAdmin && (
          <button onClick={() => setShowCreateDialog(true)}>
            Create Album
          </button>
        )}
      </div>

      <div className="albums-grid">
        {albums.map(album => (
          <div
            key={album.id}
            className="album-card"
            onClick={() => selectAlbum(album.id)}
          >
            <div className="album-cover">
              {album.cover_image_url ? (
                <img src={album.cover_image_url} alt={album.name} />
              ) : (
                <div className="album-placeholder">
                  {album.image_count} images
                </div>
              )}
            </div>

            <div className="album-info">
              <h3>{album.name}</h3>
              <p>{album.description}</p>
              <div className="album-meta">
                <span>{album.image_count} images</span>
                {album.is_training_source && (
                  <span className="training-badge">Training Source</span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {showCreateDialog && (
        <CreateAlbumDialog
          onClose={() => setShowCreateDialog(false)}
          onCreate={createAlbum}
        />
      )}
    </div>
  )
}

function AlbumDetailView({ album, onBack, isAdmin }) {
  const [images, setImages] = useState(album.images || [])
  const [selectedImages, setSelectedImages] = useState([])
  const [nsfwSetting, setNsfwSetting] = useState('blur') // 'hide', 'blur', 'show'

  const toggleImageSelection = (imageId) => {
    if (selectedImages.includes(imageId)) {
      setSelectedImages(selectedImages.filter(id => id !== imageId))
    } else {
      setSelectedImages([...selectedImages, imageId])
    }
  }

  const removeSelectedImages = async () => {
    for (const imageId of selectedImages) {
      await fetch(`/api/albums/${album.id}/images/${imageId}`, {
        method: 'DELETE',
        credentials: 'include'
      })
    }

    setImages(images.filter(img => !selectedImages.includes(img.id)))
    setSelectedImages([])
  }

  return (
    <div className="album-detail">
      <div className="album-detail-header">
        <button onClick={onBack}>← Back</button>
        <h2>{album.name}</h2>

        <div className="nsfw-filter">
          <label>NSFW:</label>
          <select value={nsfwSetting} onChange={e => setNsfwSetting(e.target.value)}>
            <option value="hide">Hide</option>
            <option value="blur">Blur</option>
            <option value="show">Show</option>
          </select>
        </div>

        {isAdmin && selectedImages.length > 0 && (
          <button onClick={removeSelectedImages}>
            Remove {selectedImages.length} images
          </button>
        )}
      </div>

      <div className="album-images-grid">
        {images.map(image => (
          <div
            key={image.id}
            className={`image-card ${image.nsfw_flag ? 'nsfw' : ''} ${nsfwSetting}`}
            onClick={() => isAdmin && toggleImageSelection(image.id)}
          >
            {isAdmin && (
              <input
                type="checkbox"
                checked={selectedImages.includes(image.id)}
                onChange={() => toggleImageSelection(image.id)}
              />
            )}

            <img
              src={image.thumbnail_url}
              alt={image.filename}
              className={image.nsfw_flag && nsfwSetting === 'blur' ? 'blurred' : ''}
            />

            {image.nsfw_flag && (
              <div className="nsfw-badge">18+</div>
            )}

            {image.labels && image.labels.length > 0 && (
              <div className="has-labels-badge">🏷️</div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

export default AlbumsTab

// web/src/styles/AlbumsTab.css (NEW FILE)
.albums-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 1rem;
  padding: 1rem;
}

.album-card {
  border: 1px solid #ddd;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.2s;
}

.album-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.album-cover {
  width: 100%;
  height: 200px;
  background: #f5f5f5;
  display: flex;
  align-items: center;
  justify-content: center;
}

.album-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.image-card.nsfw.blur img {
  filter: blur(20px);
}

.image-card.nsfw.hide {
  display: none;
}

.nsfw-badge {
  position: absolute;
  top: 8px;
  right: 8px;
  background: red;
  color: white;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: bold;
}
```

**Phase 2 Deliverables:**
- ✅ Album CRUD API endpoints
- ✅ Image upload functionality
- ✅ Album UI with grid view
- ✅ Image selection and organization
- ✅ NSFW blur/hide/show toggle
- ✅ Thumbnail generation

---

### Phase 3: AI Labeling System (Week 3, 15-20 hours)

**Goal:** Integrate Claude vision for image captioning and NSFW detection

#### 3.1 Claude Labeling Integration (8 hours)

```python
# server/tasks/labeling.py (NEW FILE)
"""AI-powered image labeling with Claude"""

from anthropic import Anthropic
from PIL import Image as PILImage
import base64
from io import BytesIO
from server.celery_app import celery
from server.database import db, Image, Label
import logging

logger = logging.getLogger(__name__)

anthropic = Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))

def encode_image(image_path):
    """Encode image to base64 for Claude API"""
    with PILImage.open(image_path) as img:
        # Resize if too large (max 1568px on longest side)
        max_size = 1568
        if max(img.size) > max_size:
            ratio = max_size / max(img.size)
            new_size = tuple(int(dim * ratio) for dim in img.size)
            img = img.resize(new_size, PILImage.LANCZOS)

        # Convert to RGB if needed
        if img.mode != 'RGB':
            img = img.convert('RGB')

        # Encode
        buffer = BytesIO()
        img.save(buffer, format='JPEG', quality=90)
        return base64.b64encode(buffer.getvalue()).decode('utf-8')

@celery.task(bind=True, name='tasks.label_image')
def label_image_task(self, image_id, prompt_type='default'):
    """
    Label a single image with Claude vision.

    Args:
        image_id: Database ID of image to label
        prompt_type: Type of prompt ('default', 'sd_training', 'detailed')
    """
    from server.api import app

    with app.app_context():
        image = Image.query.get(image_id)
        if not image:
            return {'status': 'error', 'message': 'Image not found'}

        logger.info(f"Labeling image {image_id}: {image.filename}")

        # Encode image
        try:
            image_data = encode_image(image.path)
        except Exception as e:
            logger.error(f"Failed to encode image: {e}")
            return {'status': 'error', 'message': f'Image encoding failed: {e}'}

        # Select prompt based on type
        prompts = {
            'default': """Analyze this image and provide:
1. A detailed description suitable for AI training (2-3 sentences)
2. NSFW rating: SAFE, SUGGESTIVE, ADULT, or EXPLICIT
3. 5-10 relevant tags (comma-separated)

Format:
DESCRIPTION: [description]
NSFW: [rating]
TAGS: [tags]""",

            'sd_training': """You are creating training captions for Stable Diffusion 1.5.

Analyze this image and write a detailed, factual description suitable for AI training. Focus on:
- Visual elements (colors, composition, style)
- Subject matter (what is depicted)
- Artistic style or medium
- Notable details

Also provide:
- NSFW rating: SAFE, SUGGESTIVE, ADULT, or EXPLICIT
- 5-10 descriptive tags

Format:
CAPTION: [one detailed paragraph]
NSFW: [rating]
TAGS: [tags]""",

            'detailed': """Provide an extremely detailed analysis of this image including:
- Subject and composition
- Colors, lighting, and atmosphere
- Style, technique, or medium
- Mood and emotional content
- Any text or symbols visible
- NSFW rating
- Comprehensive tags

Be thorough and precise."""
        }

        prompt = prompts.get(prompt_type, prompts['default'])

        # Call Claude
        try:
            response = anthropic.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_data
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }]
            )

            result_text = response.content[0].text
            logger.info(f"Claude response: {result_text[:200]}...")

            # Parse response
            description = None
            nsfw_rating = 'SAFE'
            tags = []

            for line in result_text.split('\n'):
                line = line.strip()
                if line.startswith('DESCRIPTION:') or line.startswith('CAPTION:'):
                    description = line.split(':', 1)[1].strip()
                elif line.startswith('NSFW:'):
                    nsfw_rating = line.split(':', 1)[1].strip()
                elif line.startswith('TAGS:'):
                    tags_str = line.split(':', 1)[1].strip()
                    tags = [tag.strip() for tag in tags_str.split(',')]

            # Update image NSFW flag
            image.nsfw_flag = nsfw_rating in ['ADULT', 'EXPLICIT']
            image.nsfw_level = nsfw_rating

            # Create caption label
            if description:
                caption_label = Label(
                    image_id=image.id,
                    label_text=description,
                    label_type='caption',
                    source='claude'
                )
                db.session.add(caption_label)

            # Create tag labels
            for tag in tags:
                tag_label = Label(
                    image_id=image.id,
                    label_text=tag,
                    label_type='tag',
                    source='claude'
                )
                db.session.add(tag_label)

            db.session.commit()

            return {
                'status': 'success',
                'image_id': image_id,
                'description': description,
                'nsfw_rating': nsfw_rating,
                'tags': tags
            }

        except Exception as e:
            logger.error(f"Claude API error: {e}")
            return {'status': 'error', 'message': f'Claude API failed: {e}'}

@celery.task(bind=True, name='tasks.label_album')
def label_album_task(self, album_id, prompt_type='default', force=False):
    """
    Label all images in an album.

    Args:
        album_id: Album ID
        prompt_type: Type of prompt to use
        force: If True, re-label images that already have labels
    """
    from server.api import app
    from server.database import Album, AlbumImage

    with app.app_context():
        album = Album.query.get(album_id)
        if not album:
            return {'status': 'error', 'message': 'Album not found'}

        # Get all images in album
        images = [assoc.image for assoc in album.image_associations]

        results = {
            'total': len(images),
            'success': 0,
            'skipped': 0,
            'failed': 0
        }

        for i, image in enumerate(images):
            # Update progress
            self.update_state(
                state='PROGRESS',
                meta={'current': i + 1, 'total': len(images)}
            )

            # Skip if already labeled (unless force=True)
            if not force and image.labels:
                results['skipped'] += 1
                continue

            # Label image
            result = label_image_task(image.id, prompt_type)

            if result['status'] == 'success':
                results['success'] += 1
            else:
                results['failed'] += 1
                logger.error(f"Failed to label {image.id}: {result.get('message')}")

        return results

# server/routes/labeling.py (NEW FILE)
"""Labeling API endpoints"""

from flask import Blueprint, request, jsonify
from server.auth import require_admin, current_user
from server.database import db, Image, Label, Album
from server.tasks.labeling import label_image_task, label_album_task

labeling_bp = Blueprint('labeling', __name__, url_prefix='/api/labeling')

@labeling_bp.route("/image/<int:image_id>", methods=["POST"])
@require_admin
def label_image(image_id):
    """Trigger AI labeling for single image (admin only)"""
    data = request.json or {}
    prompt_type = data.get('prompt_type', 'default')

    # Submit task
    task = label_image_task.delay(image_id, prompt_type)

    return jsonify({
        'success': True,
        'task_id': task.id,
        'message': 'Labeling started'
    }), 201

@labeling_bp.route("/album/<int:album_id>", methods=["POST"])
@require_admin
def label_album(album_id):
    """Trigger AI labeling for entire album (admin only)"""
    data = request.json or {}
    prompt_type = data.get('prompt_type', 'sd_training')
    force = data.get('force', False)

    # Submit task
    task = label_album_task.delay(album_id, prompt_type, force)

    return jsonify({
        'success': True,
        'task_id': task.id,
        'message': 'Batch labeling started'
    }), 201

@labeling_bp.route("/task/<task_id>", methods=["GET"])
def get_labeling_task_status(task_id):
    """Get labeling task status (public)"""
    from server.celery_app import celery as celery_app

    task = celery_app.AsyncResult(task_id)

    response = {
        'task_id': task_id,
        'status': task.state
    }

    if task.state == 'PROGRESS':
        response['progress'] = task.info
    elif task.state == 'SUCCESS':
        response['result'] = task.result
    elif task.state == 'FAILURE':
        response['error'] = str(task.info)

    return jsonify(response)

# server/api.py - Register blueprint
from server.routes.labeling import labeling_bp
app.register_blueprint(labeling_bp)
```

#### 3.2 Labeling UI (7 hours)

```javascript
// web/src/components/LabelingPanel.jsx (NEW FILE)
import React, { useState } from 'react'
import '../styles/LabelingPanel.css'

function LabelingPanel({ image, onClose, isAdmin }) {
  const [labels, setLabels] = useState(image.labels || [])
  const [newLabel, setNewLabel] = useState('')
  const [isLabeling, setIsLabeling] = useState(false)

  const triggerAILabeling = async (promptType = 'default') => {
    setIsLabeling(true)

    const response = await fetch(`/api/labeling/image/${image.id}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ prompt_type: promptType })
    })

    const data = await response.json()

    // Poll for completion
    const checkStatus = async () => {
      const statusResponse = await fetch(`/api/labeling/task/${data.task_id}`)
      const status = await statusResponse.json()

      if (status.status === 'SUCCESS') {
        // Reload labels
        const imageResponse = await fetch(`/api/images/${image.id}`)
        const imageData = await imageResponse.json()
        setLabels(imageData.labels)
        setIsLabeling(false)
      } else if (status.status === 'FAILURE') {
        alert('AI labeling failed')
        setIsLabeling(false)
      } else {
        setTimeout(checkStatus, 2000)
      }
    }

    checkStatus()
  }

  const addManualLabel = async () => {
    if (!newLabel.trim()) return

    const response = await fetch(`/api/images/${image.id}/labels`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({
        text: newLabel,
        type: 'tag',
        source: 'manual'
      })
    })

    const label = await response.json()
    setLabels([...labels, label])
    setNewLabel('')
  }

  const deleteLabel = async (labelId) => {
    await fetch(`/api/images/${image.id}/labels/${labelId}`, {
      method: 'DELETE',
      credentials: 'include'
    })

    setLabels(labels.filter(l => l.id !== labelId))
  }

  return (
    <div className="labeling-panel">
      <div className="panel-header">
        <h3>Labels & Captions</h3>
        <button onClick={onClose}>✕</button>
      </div>

      <div className="panel-content">
        {/* Image preview */}
        <div className="image-preview">
          <img src={image.url} alt={image.filename} />
          {image.nsfw_flag && (
            <div className="nsfw-badge">18+ {image.nsfw_level}</div>
          )}
        </div>

        {/* AI Labeling */}
        {isAdmin && (
          <div className="ai-labeling-section">
            <h4>AI Labeling</h4>
            <div className="ai-buttons">
              <button
                onClick={() => triggerAILabeling('default')}
                disabled={isLabeling}
              >
                {isLabeling ? 'Labeling...' : 'Quick Label'}
              </button>
              <button
                onClick={() => triggerAILabeling('sd_training')}
                disabled={isLabeling}
              >
                SD Training Caption
              </button>
              <button
                onClick={() => triggerAILabeling('detailed')}
                disabled={isLabeling}
              >
                Detailed Analysis
              </button>
            </div>
          </div>
        )}

        {/* Existing labels */}
        <div className="labels-section">
          <h4>Labels</h4>

          {/* Caption */}
          {labels.filter(l => l.type === 'caption').map(label => (
            <div key={label.id} className="caption-label">
              <p>{label.text}</p>
              <div className="label-meta">
                <span className="source-badge">{label.source}</span>
                {isAdmin && (
                  <button onClick={() => deleteLabel(label.id)}>Delete</button>
                )}
              </div>
            </div>
          ))}

          {/* Tags */}
          <div className="tags-list">
            {labels.filter(l => l.type === 'tag').map(label => (
              <div key={label.id} className="tag-chip">
                <span>{label.text}</span>
                {isAdmin && (
                  <button onClick={() => deleteLabel(label.id)}>✕</button>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Manual label input */}
        {isAdmin && (
          <div className="manual-label-section">
            <h4>Add Manual Tag</h4>
            <div className="input-group">
              <input
                type="text"
                value={newLabel}
                onChange={e => setNewLabel(e.target.value)}
                onKeyPress={e => e.key === 'Enter' && addManualLabel()}
                placeholder="Enter tag..."
              />
              <button onClick={addManualLabel}>Add</button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default LabelingPanel

// Update AlbumDetailView to show labeling panel
function AlbumDetailView({ album, onBack, isAdmin }) {
  const [selectedImage, setSelectedImage] = useState(null)
  const [showBatchLabelDialog, setShowBatchLabelDialog] = useState(false)

  // ...existing code...

  const batchLabelAlbum = async (promptType) => {
    const response = await fetch(`/api/labeling/album/${album.id}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ prompt_type: promptType })
    })

    const data = await response.json()
    alert(`Batch labeling started. Task ID: ${data.task_id}`)
    setShowBatchLabelDialog(false)
  }

  return (
    <div className="album-detail">
      {/* ...existing header... */}

      {isAdmin && (
        <button onClick={() => setShowBatchLabelDialog(true)}>
          Batch Label Album
        </button>
      )}

      {/* ...existing images grid... */}

      {selectedImage && (
        <LabelingPanel
          image={selectedImage}
          onClose={() => setSelectedImage(null)}
          isAdmin={isAdmin}
        />
      )}

      {showBatchLabelDialog && (
        <BatchLabelDialog
          onClose={() => setShowBatchLabelDialog(false)}
          onSubmit={batchLabelAlbum}
        />
      )}
    </div>
  )
}
```

**Phase 3 Deliverables:**
- ✅ Claude vision integration
- ✅ AI labeling for single images
- ✅ Batch labeling for albums
- ✅ NSFW detection and classification
- ✅ Manual label editing
- ✅ Label display in gallery

---

### Phase 4: Web Scraping Integration (Week 4, 15-20 hours)

**Goal:** Integrate existing training-data scraper into Imagineer

#### 4.1 Scraper Integration (10 hours)

```python
# server/tasks/scraping.py (NEW FILE)
"""Web scraping integration"""

from server.celery_app import celery
from server.database import db, ScrapeJob, Album, Image, AlbumImage, Label
from pathlib import Path
import subprocess
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

TRAINING_DATA_PATH = Path('/home/jdubz/Development/training-data')

@celery.task(bind=True, name='tasks.scrape_site')
def scrape_site_task(self, scrape_job_id):
    """
    Execute web scraping job using training-data project.

    Args:
        scrape_job_id: Database ID of scrape job
    """
    from server.api import app

    with app.app_context():
        job = ScrapeJob.query.get(scrape_job_id)
        if not job:
            return {'status': 'error', 'message': 'Job not found'}

        job.status = 'running'
        job.started_at = datetime.utcnow()
        db.session.commit()

        logger.info(f"Starting scrape job {scrape_job_id}: {job.url}")

        # Create output directory
        output_dir = Path(f'/mnt/storage/imagineer/scraped/job_{scrape_job_id}')
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Run training-data scraper
            cmd = [
                'python', '-m', 'training_data',
                '--url', job.url,
                '--output', str(output_dir),
                '--depth', str(job.depth),
                '--config', str(TRAINING_DATA_PATH / 'config/default_config.yaml')
            ]

            process = subprocess.Popen(
                cmd,
                cwd=TRAINING_DATA_PATH,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            # Stream output and update progress
            for line in process.stdout:
                logger.info(f"Scraper: {line.strip()}")

                # Parse progress from output
                if 'Discovered:' in line:
                    # Extract count
                    count = int(line.split('Discovered:')[1].split()[0])
                    job.images_discovered = count
                elif 'Downloaded:' in line:
                    count = int(line.split('Downloaded:')[1].split()[0])
                    job.images_downloaded = count

                    # Update task progress
                    self.update_state(
                        state='PROGRESS',
                        meta={
                            'discovered': job.images_discovered,
                            'downloaded': job.images_downloaded
                        }
                    )

                # Update progress message
                job.progress_message = line.strip()[-200:]  # Last 200 chars
                db.session.commit()

            process.wait()

            if process.returncode == 0:
                # Scraping successful - import results
                result = import_scraped_images(scrape_job_id, output_dir)

                job.status = 'completed'
                job.completed_at = datetime.utcnow()
                job.images_filtered = result['imported']
                db.session.commit()

                return {
                    'status': 'success',
                    'images_imported': result['imported'],
                    'album_id': result['album_id']
                }
            else:
                job.status = 'failed'
                job.completed_at = datetime.utcnow()
                job.progress_message = f'Scraper failed with code {process.returncode}'
                db.session.commit()

                return {'status': 'error', 'message': 'Scraper failed'}

        except Exception as e:
            logger.error(f"Scrape job error: {e}")
            job.status = 'failed'
            job.completed_at = datetime.utcnow()
            job.progress_message = str(e)
            db.session.commit()

            return {'status': 'error', 'message': str(e)}

def import_scraped_images(scrape_job_id, output_dir):
    """
    Import scraped images into database and create album.

    Args:
        scrape_job_id: Scrape job ID
        output_dir: Path to scraped images directory

    Returns:
        Dict with import results
    """
    from server.database import db, Album, Image, AlbumImage, Label

    job = ScrapeJob.query.get(scrape_job_id)

    # Create album
    album = Album(
        name=f"Scraped: {job.album_name}",
        description=f"Images scraped from {job.url}",
        is_training_source=True,  # Default to training source
        created_by=job.created_by
    )
    db.session.add(album)
    db.session.flush()

    images_dir = output_dir / 'images'
    if not images_dir.exists():
        return {'imported': 0, 'album_id': album.id}

    imported_count = 0

    # Import all images
    for image_file in images_dir.glob('*.jpg'):
        caption_file = image_file.with_suffix('.txt')

        # Read caption if exists
        caption = None
        if caption_file.exists():
            caption = caption_file.read_text().strip()

        # Get image dimensions
        from PIL import Image as PILImage
        with PILImage.open(image_file) as img:
            width, height = img.size

        # Create image record
        import hashlib
        sha256 = hashlib.sha256()
        with open(image_file, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)

        image = Image(
            filename=image_file.name,
            path=str(image_file),
            source_type='scraped',
            source_id=f'job_{scrape_job_id}',
            width=width,
            height=height,
            file_size=image_file.stat().st_size,
            checksum=sha256.hexdigest()
        )
        db.session.add(image)
        db.session.flush()

        # Add caption as label if exists
        if caption:
            label = Label(
                image_id=image.id,
                label_text=caption,
                label_type='caption',
                source='scraper'
            )
            db.session.add(label)

        # Add to album
        assoc = AlbumImage(
            album_id=album.id,
            image_id=image.id,
            added_by=job.created_by
        )
        db.session.add(assoc)

        imported_count += 1

    db.session.commit()

    logger.info(f"Imported {imported_count} images from scrape job {scrape_job_id}")

    return {
        'imported': imported_count,
        'album_id': album.id
    }

# server/routes/scraping.py (NEW FILE)
"""Web scraping API endpoints"""

from flask import Blueprint, request, jsonify
from server.auth import require_admin, current_user
from server.database import db, ScrapeJob
from server.tasks.scraping import scrape_site_task

scraping_bp = Blueprint('scraping', __name__, url_prefix='/api/scraping')

@scraping_bp.route("/start", methods=["POST"])
@require_admin
def start_scrape():
    """Start web scraping job (admin only)"""
    data = request.json

    # Validate URL
    url = data.get('url')
    if not url:
        return jsonify({'error': 'URL required'}), 400

    # Create job record
    job = ScrapeJob(
        url=url,
        album_name=data.get('album_name', f'Scraped {url}'),
        depth=data.get('depth', 3),
        created_by=current_user.email
    )

    db.session.add(job)
    db.session.commit()

    # Submit task
    task = scrape_site_task.delay(job.id)
    job.celery_task_id = task.id
    db.session.commit()

    return jsonify({
        'success': True,
        'job_id': job.id,
        'task_id': task.id
    }), 201

@scraping_bp.route("/jobs", methods=["GET"])
def list_scrape_jobs():
    """List all scrape jobs (public)"""
    jobs = ScrapeJob.query.order_by(ScrapeJob.created_at.desc()).limit(50).all()
    return jsonify({
        'jobs': [job.to_dict() for job in jobs]
    })

@scraping_bp.route("/jobs/<int:job_id>", methods=["GET"])
def get_scrape_job(job_id):
    """Get scrape job status (public)"""
    job = ScrapeJob.query.get_or_404(job_id)
    return jsonify(job.to_dict())

@scraping_bp.route("/jobs/<int:job_id>/cancel", methods=["POST"])
@require_admin
def cancel_scrape_job(job_id):
    """Cancel running scrape job (admin only)"""
    job = ScrapeJob.query.get_or_404(job_id)

    if job.celery_task_id:
        from server.celery_app import celery as celery_app
        celery_app.control.revoke(job.celery_task_id, terminate=True)

    job.status = 'cancelled'
    db.session.commit()

    return jsonify({'success': True})

# server/api.py - Register blueprint
from server.routes.scraping import scraping_bp
app.register_blueprint(scraping_bp)
```

#### 4.2 Scraping UI (5-7 hours)

```javascript
// web/src/components/ScrapingTab.jsx (NEW FILE)
import React, { useState, useEffect } from 'react'
import '../styles/ScrapingTab.css'

function ScrapingTab({ isAdmin }) {
  const [scrapeJobs, setScrapeJobs] = useState([])
  const [showStartDialog, setShowStartDialog] = useState(false)

  useEffect(() => {
    fetchJobs()

    // Auto-refresh every 5 seconds
    const interval = setInterval(fetchJobs, 5000)
    return () => clearInterval(interval)
  }, [])

  const fetchJobs = async () => {
    const response = await fetch('/api/scraping/jobs')
    const data = await response.json()
    setScrapeJobs(data.jobs)
  }

  const startScrape = async (url, albumName, depth) => {
    const response = await fetch('/api/scraping/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ url, album_name: albumName, depth })
    })

    if (response.ok) {
      fetchJobs()
      setShowStartDialog(false)
    }
  }

  const cancelJob = async (jobId) => {
    await fetch(`/api/scraping/jobs/${jobId}/cancel`, {
      method: 'POST',
      credentials: 'include'
    })
    fetchJobs()
  }

  return (
    <div className="scraping-tab">
      <div className="scraping-header">
        <h2>Web Scraping</h2>
        {isAdmin && (
          <button onClick={() => setShowStartDialog(true)}>
            Start New Scrape
          </button>
        )}
      </div>

      <div className="scrape-jobs-list">
        {scrapeJobs.map(job => (
          <div key={job.id} className={`scrape-job-card status-${job.status}`}>
            <div className="job-header">
              <h3>{job.album_name}</h3>
              <span className={`status-badge ${job.status}`}>
                {job.status}
              </span>
            </div>

            <div className="job-details">
              <div className="detail">
                <strong>URL:</strong>
                <a href={job.url} target="_blank" rel="noopener noreferrer">
                  {job.url}
                </a>
              </div>

              {job.status === 'running' && (
                <div className="progress-section">
                  <div className="stats">
                    <span>Discovered: {job.stats.discovered}</span>
                    <span>Downloaded: {job.stats.downloaded}</span>
                  </div>
                  <p className="progress-message">{job.progress}</p>
                </div>
              )}

              {job.status === 'completed' && (
                <div className="stats">
                  <span>✓ {job.stats.filtered} images imported</span>
                </div>
              )}

              <div className="job-meta">
                <span>Started: {new Date(job.created_at).toLocaleString()}</span>
                {job.completed_at && (
                  <span>
                    Completed: {new Date(job.completed_at).toLocaleString()}
                  </span>
                )}
              </div>
            </div>

            {isAdmin && job.status === 'running' && (
              <button onClick={() => cancelJob(job.id)}>Cancel</button>
            )}
          </div>
        ))}
      </div>

      {showStartDialog && (
        <StartScrapeDialog
          onClose={() => setShowStartDialog(false)}
          onSubmit={startScrape}
        />
      )}
    </div>
  )
}

function StartScrapeDialog({ onClose, onSubmit }) {
  const [url, setUrl] = useState('')
  const [albumName, setAlbumName] = useState('')
  const [depth, setDepth] = useState(3)

  const handleSubmit = () => {
    if (!url) return
    onSubmit(url, albumName || `Scraped ${url}`, depth)
  }

  return (
    <div className="dialog-overlay" onClick={onClose}>
      <div className="dialog" onClick={e => e.stopPropagation()}>
        <h2>Start Web Scrape</h2>

        <div className="form-group">
          <label>URL to Scrape:</label>
          <input
            type="url"
            value={url}
            onChange={e => setUrl(e.target.value)}
            placeholder="https://example.com/gallery"
            required
          />
        </div>

        <div className="form-group">
          <label>Album Name:</label>
          <input
            type="text"
            value={albumName}
            onChange={e => setAlbumName(e.target.value)}
            placeholder="Auto-generated from URL"
          />
        </div>

        <div className="form-group">
          <label>Max Depth:</label>
          <input
            type="number"
            value={depth}
            onChange={e => setDepth(parseInt(e.target.value))}
            min="1"
            max="10"
          />
          <small>How many links deep to follow (1-10)</small>
        </div>

        <div className="dialog-actions">
          <button onClick={handleSubmit}>Start Scrape</button>
          <button onClick={onClose}>Cancel</button>
        </div>
      </div>
    </div>
  )
}

export default ScrapingTab
```

**Phase 4 Deliverables:**
- ✅ Training-data scraper integrated
- ✅ Scraping job tracking in database
- ✅ Progress monitoring UI
- ✅ Auto-import to albums
- ✅ Captions from scraper preserved

---

### Phase 5: Training Pipeline (Week 5-6, 20-25 hours)

**Goal:** UI-driven LoRA training from albums

#### 5.1 Training Integration (12 hours)

```python
# server/tasks/training.py (NEW FILE)
"""LoRA training task integration"""

from server.celery_app import celery
from server.database import db, TrainingRun, Album, AlbumImage, Image, Label
from pathlib import Path
import subprocess
import shutil
import logging
from datetime import datetime
import json

logger = logging.getLogger(__name__)

@celery.task(bind=True, name='tasks.train_lora')
def train_lora_task(self, training_run_id):
    """
    Execute LoRA training from albums.

    Args:
        training_run_id: Database ID of training run
    """
    from server.api import app

    with app.app_context():
        run = TrainingRun.query.get(training_run_id)
        if not run:
            return {'status': 'error', 'message': 'Training run not found'}

        run.status = 'running'
        run.started_at = datetime.utcnow()
        db.session.commit()

        logger.info(f"Starting training run {training_run_id}: {run.name}")

        try:
            # Prepare training data
            training_dir = prepare_training_data(run)

            # Build training command
            output_dir = Path(f'/mnt/speedy/imagineer/models/lora/trained_{training_run_id}')
            output_dir.mkdir(parents=True, exist_ok=True)

            config = run.config or {}

            cmd = [
                'python', 'examples/train_lora.py',
                '--data-dir', str(training_dir),
                '--output-dir', str(output_dir),
                '--steps', str(config.get('steps', 1000)),
                '--rank', str(config.get('rank', 4)),
                '--learning-rate', str(config.get('learning_rate', 1e-4)),
                '--batch-size', str(config.get('batch_size', 1))
            ]

            logger.info(f"Training command: {' '.join(cmd)}")

            # Execute training
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=Path(__file__).parent.parent.parent
            )

            # Stream output and update progress
            logs = []
            for line in process.stdout:
                logs.append(line)
                logger.info(f"Training: {line.strip()}")

                # Parse progress
                if 'Step' in line and '/' in line:
                    try:
                        # Extract step number (e.g., "Step 100/1000")
                        parts = line.split('Step')[1].split('/')
                        current_step = int(parts[0].strip())
                        total_steps = int(parts[1].split()[0])

                        run.current_step = current_step
                        run.total_steps = total_steps
                        run.progress_percentage = (current_step / total_steps) * 100

                        # Update task progress
                        self.update_state(
                            state='PROGRESS',
                            meta={
                                'current_step': current_step,
                                'total_steps': total_steps,
                                'percentage': run.progress_percentage
                            }
                        )

                        db.session.commit()
                    except:
                        pass

            process.wait()

            # Save logs
            run.training_logs = '\n'.join(logs[-500:])  # Last 500 lines

            if process.returncode == 0:
                # Training successful
                lora_files = list(output_dir.glob('*.safetensors'))

                if lora_files:
                    run.output_lora_path = str(lora_files[0])
                    run.status = 'completed'
                else:
                    run.status = 'failed'
                    run.training_logs += '\n\nNo LoRA file generated'
            else:
                run.status = 'failed'
                run.training_logs += f'\n\nTraining failed with exit code {process.returncode}'

            run.completed_at = datetime.utcnow()
            db.session.commit()

            return {
                'status': run.status,
                'output_lora_path': run.output_lora_path
            }

        except Exception as e:
            logger.error(f"Training error: {e}")
            run.status = 'failed'
            run.completed_at = datetime.utcnow()
            run.training_logs = str(e)
            db.session.commit()

            return {'status': 'error', 'message': str(e)}

def prepare_training_data(training_run):
    """
    Prepare training dataset from albums.

    Creates a directory with image files and corresponding .txt caption files
    in Stable Diffusion 1.5 format.

    Args:
        training_run: TrainingRun database record

    Returns:
        Path to training data directory
    """
    # Create training data directory
    training_dir = Path(f'/mnt/speedy/imagineer/training_data/run_{training_run.id}')
    training_dir.mkdir(parents=True, exist_ok=True)

    # Get all images from specified albums
    album_ids = training_run.album_ids

    images = db.session.query(Image).join(AlbumImage).filter(
        AlbumImage.album_id.in_(album_ids)
    ).all()

    logger.info(f"Preparing {len(images)} images for training")

    for idx, image in enumerate(images):
        # Copy image file
        src_path = Path(image.path)
        dest_filename = f"image_{idx:04d}{src_path.suffix}"
        dest_path = training_dir / dest_filename

        shutil.copy2(src_path, dest_path)

        # Create caption file
        caption = get_training_caption(image)
        caption_path = dest_path.with_suffix('.txt')
        caption_path.write_text(caption)

    logger.info(f"Training data prepared in {training_dir}")

    return training_dir

def get_training_caption(image):
    """
    Get training caption for image.

    Priority:
    1. AI-generated caption label
    2. Manual caption label
    3. Generation prompt (if generated)
    4. Filename as fallback

    Args:
        image: Image database record

    Returns:
        Caption string
    """
    # Look for caption labels
    caption_labels = [l for l in image.labels if l.label_type == 'caption']

    if caption_labels:
        # Prefer AI captions from Claude or scraper
        ai_captions = [l for l in caption_labels if l.source in ['claude', 'scraper']]
        if ai_captions:
            return ai_captions[0].label_text

        # Otherwise use manual caption
        return caption_labels[0].label_text

    # Fall back to generation prompt if available
    if image.prompt:
        return image.prompt

    # Last resort: filename
    return Path(image.filename).stem.replace('_', ' ')

# server/routes/training.py (NEW FILE)
"""Training API endpoints"""

from flask import Blueprint, request, jsonify
from server.auth import require_admin, current_user
from server.database import db, TrainingRun, Album
from server.tasks.training import train_lora_task

training_bp = Blueprint('training', __name__, url_prefix='/api/training')

@training_bp.route("/start", methods=["POST"])
@require_admin
def start_training():
    """Start LoRA training (admin only)"""
    data = request.json

    # Validate albums
    album_ids = data.get('album_ids', [])
    if not album_ids:
        return jsonify({'error': 'At least one album required'}), 400

    # Verify albums exist and have images
    albums = Album.query.filter(Album.id.in_(album_ids)).all()
    if len(albums) != len(album_ids):
        return jsonify({'error': 'Invalid album IDs'}), 400

    total_images = sum(album.image_count for album in albums)
    if total_images == 0:
        return jsonify({'error': 'Selected albums have no images'}), 400

    # Create training run record
    run = TrainingRun(
        name=data.get('name', f'Training {datetime.now().strftime("%Y%m%d_%H%M")}'),
        album_ids=album_ids,
        config=data.get('config', {
            'steps': 1000,
            'rank': 4,
            'learning_rate': 1e-4,
            'batch_size': 1
        }),
        total_steps=data.get('config', {}).get('steps', 1000),
        created_by=current_user.email
    )

    db.session.add(run)
    db.session.commit()

    # Submit task
    task = train_lora_task.delay(run.id)
    run.celery_task_id = task.id
    db.session.commit()

    return jsonify({
        'success': True,
        'training_run_id': run.id,
        'task_id': task.id,
        'message': f'Training started with {total_images} images'
    }), 201

@training_bp.route("/runs", methods=["GET"])
def list_training_runs():
    """List training runs (public)"""
    runs = TrainingRun.query.order_by(TrainingRun.created_at.desc()).limit(50).all()
    return jsonify({
        'training_runs': [run.to_dict() for run in runs]
    })

@training_bp.route("/runs/<int:run_id>", methods=["GET"])
def get_training_run(run_id):
    """Get training run details (public)"""
    run = TrainingRun.query.get_or_404(run_id)
    return jsonify(run.to_dict())

@training_bp.route("/runs/<int:run_id>/cancel", methods=["POST"])
@require_admin
def cancel_training_run(run_id):
    """Cancel training run (admin only)"""
    run = TrainingRun.query.get_or_404(run_id)

    if run.celery_task_id:
        from server.celery_app import celery as celery_app
        celery_app.control.revoke(run.celery_task_id, terminate=True, signal='SIGKILL')

    run.status = 'cancelled'
    db.session.commit()

    return jsonify({'success': True})

# server/api.py - Register blueprint
from server.routes.training import training_bp
app.register_blueprint(training_bp)
```

#### 5.2 Training UI (8 hours)

```javascript
// web/src/components/TrainingTab.jsx (NEW FILE)
import React, { useState, useEffect } from 'react'
import '../styles/TrainingTab.css'

function TrainingTab({ isAdmin }) {
  const [trainingRuns, setTrainingRuns] = useState([])
  const [albums, setAlbums] = useState([])
  const [showStartDialog, setShowStartDialog] = useState(false)

  useEffect(() => {
    fetchRuns()
    fetchAlbums()

    // Auto-refresh every 3 seconds
    const interval = setInterval(fetchRuns, 3000)
    return () => clearInterval(interval)
  }, [])

  const fetchRuns = async () => {
    const response = await fetch('/api/training/runs')
    const data = await response.json()
    setTrainingRuns(data.training_runs)
  }

  const fetchAlbums = async () => {
    const response = await fetch('/api/albums')
    const data = await response.json()
    // Filter to training source albums
    setAlbums(data.albums.filter(a => a.is_training_source))
  }

  const startTraining = async (name, albumIds, config) => {
    const response = await fetch('/api/training/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ name, album_ids: albumIds, config })
    })

    if (response.ok) {
      fetchRuns()
      setShowStartDialog(false)
    } else {
      const error = await response.json()
      alert(error.error)
    }
  }

  const cancelRun = async (runId) => {
    await fetch(`/api/training/runs/${runId}/cancel`, {
      method: 'POST',
      credentials: 'include'
    })
    fetchRuns()
  }

  return (
    <div className="training-tab">
      <div className="training-header">
        <h2>LoRA Training</h2>
        {isAdmin && (
          <button onClick={() => setShowStartDialog(true)}>
            Start Training
          </button>
        )}
      </div>

      <div className="training-runs-list">
        {trainingRuns.map(run => (
          <div key={run.id} className={`training-run-card status-${run.status}`}>
            <div className="run-header">
              <h3>{run.name}</h3>
              <span className={`status-badge ${run.status}`}>
                {run.status}
              </span>
            </div>

            <div className="run-details">
              {run.status === 'running' && (
                <div className="progress-section">
                  <div className="progress-bar">
                    <div
                      className="progress-fill"
                      style={{ width: `${run.progress}%` }}
                    />
                  </div>
                  <div className="progress-stats">
                    <span>Step {run.current_step} / {run.total_steps}</span>
                    <span>{run.progress.toFixed(1)}%</span>
                  </div>
                </div>
              )}

              {run.status === 'completed' && (
                <div className="completion-info">
                  <p>✓ Training completed successfully</p>
                  <div className="output-path">
                    <strong>Output:</strong>
                    <code>{run.output_lora_path}</code>
                  </div>
                </div>
              )}

              <div className="run-config">
                <h4>Configuration:</h4>
                <div className="config-grid">
                  <div><strong>Steps:</strong> {run.config?.steps || 1000}</div>
                  <div><strong>Rank:</strong> {run.config?.rank || 4}</div>
                  <div><strong>Learning Rate:</strong> {run.config?.learning_rate || '1e-4'}</div>
                  <div><strong>Batch Size:</strong> {run.config?.batch_size || 1}</div>
                </div>
              </div>

              <div className="run-meta">
                <span>Started: {new Date(run.created_at).toLocaleString()}</span>
                {run.completed_at && (
                  <span>
                    Completed: {new Date(run.completed_at).toLocaleString()}
                  </span>
                )}
              </div>
            </div>

            {isAdmin && run.status === 'running' && (
              <button
                className="cancel-button"
                onClick={() => cancelRun(run.id)}
              >
                Cancel Training
              </button>
            )}
          </div>
        ))}
      </div>

      {showStartDialog && (
        <StartTrainingDialog
          albums={albums}
          onClose={() => setShowStartDialog(false)}
          onSubmit={startTraining}
        />
      )}
    </div>
  )
}

function StartTrainingDialog({ albums, onClose, onSubmit }) {
  const [name, setName] = useState(`LoRA ${new Date().toISOString().split('T')[0]}`)
  const [selectedAlbums, setSelectedAlbums] = useState([])
  const [config, setConfig] = useState({
    steps: 1000,
    rank: 4,
    learning_rate: 0.0001,
    batch_size: 1
  })

  const toggleAlbum = (albumId) => {
    if (selectedAlbums.includes(albumId)) {
      setSelectedAlbums(selectedAlbums.filter(id => id !== albumId))
    } else {
      setSelectedAlbums([...selectedAlbums, albumId])
    }
  }

  const totalImages = albums
    .filter(a => selectedAlbums.includes(a.id))
    .reduce((sum, a) => sum + a.image_count, 0)

  const handleSubmit = () => {
    if (selectedAlbums.length === 0) {
      alert('Select at least one album')
      return
    }
    onSubmit(name, selectedAlbums, config)
  }

  return (
    <div className="dialog-overlay" onClick={onClose}>
      <div className="dialog large" onClick={e => e.stopPropagation()}>
        <h2>Start LoRA Training</h2>

        <div className="form-group">
          <label>Training Name:</label>
          <input
            type="text"
            value={name}
            onChange={e => setName(e.target.value)}
            placeholder="e.g., Card Deck Style"
          />
        </div>

        <div className="form-group">
          <label>Select Training Albums:</label>
          <div className="albums-selection">
            {albums.map(album => (
              <div
                key={album.id}
                className={`album-option ${selectedAlbums.includes(album.id) ? 'selected' : ''}`}
                onClick={() => toggleAlbum(album.id)}
              >
                <input
                  type="checkbox"
                  checked={selectedAlbums.includes(album.id)}
                  onChange={() => toggleAlbum(album.id)}
                />
                <span>{album.name}</span>
                <span className="image-count">({album.image_count} images)</span>
              </div>
            ))}
          </div>
          <p className="selection-summary">
            Selected: {selectedAlbums.length} albums, {totalImages} total images
          </p>
        </div>

        <div className="form-group">
          <label>Training Steps:</label>
          <input
            type="number"
            value={config.steps}
            onChange={e => setConfig({...config, steps: parseInt(e.target.value)})}
            min="100"
            max="10000"
            step="100"
          />
          <small>Recommended: 1000-2000 steps. Higher = better quality but longer training.</small>
        </div>

        <div className="form-group">
          <label>LoRA Rank:</label>
          <input
            type="number"
            value={config.rank}
            onChange={e => setConfig({...config, rank: parseInt(e.target.value)})}
            min="1"
            max="32"
          />
          <small>Recommended: 4-8. Higher = more capacity but larger file.</small>
        </div>

        <div className="form-group">
          <label>Learning Rate:</label>
          <input
            type="number"
            value={config.learning_rate}
            onChange={e => setConfig({...config, learning_rate: parseFloat(e.target.value)})}
            step="0.00001"
            min="0.00001"
            max="0.001"
          />
          <small>Recommended: 0.0001 (1e-4)</small>
        </div>

        <div className="warning-message">
          ⚠️ Training will pause the generation queue and may take 30-60 minutes.
          Ensure GPU is not in use.
        </div>

        <div className="dialog-actions">
          <button onClick={handleSubmit}>Start Training</button>
          <button onClick={onClose}>Cancel</button>
        </div>
      </div>
    </div>
  )
}

export default TrainingTab
```

**Phase 5 Deliverables:**
- ✅ LoRA training from albums
- ✅ Training progress monitoring
- ✅ Auto-caption generation for training
- ✅ Training configuration UI
- ✅ Trained LoRA registration

---

## Summary & Timeline

### Total Effort Estimate

| Phase | Focus | Estimated Hours | Timeline |
|-------|-------|----------------|----------|
| Phase 1 | Foundation & Security | 20-25 | Week 1 |
| Phase 2 | Album System | 20-25 | Week 2 |
| Phase 3 | AI Labeling | 15-20 | Week 3 |
| Phase 4 | Web Scraping | 15-20 | Week 4 |
| Phase 5 | Training Pipeline | 20-25 | Week 5-6 |
| **TOTAL** | **Complete Platform** | **90-115 hours** | **5-6 weeks** |

### Success Metrics

After implementation:

| Metric | Current | Target |
|--------|---------|--------|
| Public Viewing | ❌ No | ✅ Yes |
| Album System | ❌ No | ✅ Full CRUD |
| AI Labeling | ❌ No | ✅ Claude + Manual |
| Web Scraping | ⚠️ Separate project | ✅ Integrated |
| Training UI | ❌ CLI only | ✅ Full UI workflow |
| Database | ❌ Filesystem | ✅ SQLite |
| Auth Model | ⚠️ 3 roles | ✅ Public + Admin |
| NSFW Handling | ❌ No | ✅ Blur/Hide/Show |

---

## Next Steps

**Immediate Actions (This Week):**

1. ✅ Review this revised plan
2. ✅ Set up `.env` files with secrets (FLASK_SECRET_KEY, ANTHROPIC_API_KEY)
3. ✅ Start Phase 1: Security fixes (6 hours)
4. ✅ Database setup (8 hours)
5. ✅ Migrate existing images to database
6. ✅ Test public viewing

**Questions to Resolve:**

1. **Redis Setup:** Docker or native installation?
2. **Cloudflare Tunnel:** Already configured or need setup guide?
3. **Firebase Deployment:** Want help with deployment scripts?
4. **Training Priority:** Should we do scraping first to build datasets?

Let me know which phase you'd like to start with, or if you have questions about any specific component!
