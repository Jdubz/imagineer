import json

import pytest

from server.database import Album, MigrationHistory, db
from server.services.template_seeder import MIGRATION_NAME, ensure_default_set_templates


def test_ensure_default_set_templates_creates_records(app):
    with app.app_context():
        summary = ensure_default_set_templates(app)

        assert summary["created"] or summary["updated"]

        templates = Album.query.filter(Album.is_set_template.is_(True)).order_by(Album.name).all()
        names = [album.name for album in templates]
        assert "Card Deck Template" in names
        assert "Zodiac Template" in names
        assert "Tarot Deck Template" in names

        for album in templates:
            assert album.csv_data, f"{album.name} missing csv_data"
            rows = json.loads(album.csv_data)
            assert isinstance(rows, list) and rows, f"{album.name} missing template rows"

        record = MigrationHistory.query.filter_by(name=MIGRATION_NAME).one_or_none()
        assert record is not None
        assert record.details is not None

        # Running the seeder again should not create duplicates
        initial_count = Album.query.filter(Album.is_set_template.is_(True)).count()
        summary_second = ensure_default_set_templates(app)
        assert (
            Album.query.filter(Album.is_set_template.is_(True)).count() == initial_count
        ), "Seeder created duplicate templates"
        assert not summary_second["created"]


def test_template_seeder_rolls_back_on_failure(app, monkeypatch):
    with app.app_context():
        # Force database commit failure to ensure rollback safety
        original_commit = db.session.commit

        def boom():
            raise RuntimeError("commit failed")

        monkeypatch.setattr(db.session, "commit", boom)

        with pytest.raises(RuntimeError):
            ensure_default_set_templates(app)

        # Restore commit to verify tables remain empty after rollback
        monkeypatch.setattr(db.session, "commit", original_commit)
        assert Album.query.filter(Album.is_set_template.is_(True)).count() == 0
