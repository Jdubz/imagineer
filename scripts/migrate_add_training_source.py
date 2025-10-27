#!/usr/bin/env python3
"""
Migration script to add is_training_source column to albums table
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from server.database import db, init_database
from flask import Flask

def migrate_add_training_source():
    """Add is_training_source column to albums table"""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///imagineer.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    init_database(app)
    
    with app.app_context():
        try:
            # Add the column using raw SQL
            with db.engine.connect() as conn:
                conn.execute(db.text("ALTER TABLE albums ADD COLUMN is_training_source BOOLEAN DEFAULT 0"))
                conn.commit()
            print("✅ Successfully added is_training_source column to albums table")
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                print("ℹ️  Column is_training_source already exists")
            else:
                print(f"❌ Error adding column: {e}")
                return False
    
    return True

if __name__ == "__main__":
    success = migrate_add_training_source()
    sys.exit(0 if success else 1)