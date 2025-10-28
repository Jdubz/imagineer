"""
Tests for the MigrationHistory helper that tracks one-off maintenance scripts.
"""

from server.database import MigrationHistory, db


def test_migration_history_records_and_updates(app):
    """Ensure migration records are created once and timestamps refresh on subsequent runs."""
    marker_name = "test_migration_marker"

    with app.app_context():
        assert MigrationHistory.has_run(marker_name) is False

        MigrationHistory.ensure_record(marker_name, details="initial import")
        db.session.commit()

        first_record = MigrationHistory.query.filter_by(name=marker_name).first()
        assert first_record is not None
        assert first_record.details == "initial import"
        first_applied = first_record.applied_at
        first_last_run = first_record.last_run_at

        MigrationHistory.ensure_record(
            marker_name,
            details="re-run with new data",
            refresh_timestamp=True,
        )
        db.session.commit()

        updated_record = MigrationHistory.query.filter_by(name=marker_name).first()
        assert updated_record is not None
        assert updated_record.details == "re-run with new data"
        assert updated_record.applied_at == first_applied
        assert updated_record.last_run_at >= first_last_run
        assert MigrationHistory.has_run(marker_name) is True
