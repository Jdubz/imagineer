#!/usr/bin/env python3
"""Test script to verify BugReport database model"""

import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from flask import Flask  # noqa: E402

from server.database import BugReport, db, init_database  # noqa: E402


def test_bug_report_model():
    """Test BugReport database model creation and operations"""
    # Create a test app with in-memory database
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["TESTING"] = True

    # Initialize database
    init_database(app)

    with app.app_context():
        # Create all tables
        db.create_all()
        print("✅ BugReport table created successfully")

        # Test creating a bug report
        report = BugReport(
            report_id="test_bug_001",
            trace_id="trace_123",
            submitted_by="test@example.com",
            description="Test bug report for database migration",
            status="open",
            automation_attempts=0,
        )
        db.session.add(report)
        db.session.commit()
        print("✅ BugReport record created successfully")

        # Test retrieval
        retrieved = BugReport.query.filter_by(report_id="test_bug_001").first()
        assert retrieved is not None, "Failed to retrieve bug report"
        print(f"✅ BugReport retrieved: {retrieved.report_id}")
        print(f"   - Status: {retrieved.status}")
        print(f"   - Description: {retrieved.description}")
        print(f"   - Submitted by: {retrieved.submitted_by}")

        # Test to_dict method
        report_dict = retrieved.to_dict(include_context=False)
        print(f"✅ to_dict() works: {list(report_dict.keys())}")

        # Test update
        retrieved.status = "resolved"
        retrieved.resolution_notes = "Fixed by automated remediation"
        db.session.commit()
        print("✅ BugReport updated successfully")

        # Verify update
        updated = BugReport.query.filter_by(report_id="test_bug_001").first()
        assert updated.status == "resolved"
        print(f"✅ Status updated to: {updated.status}")

        print("\n🎉 All tests passed!")


if __name__ == "__main__":
    test_bug_report_model()
