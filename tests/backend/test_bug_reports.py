from server.routes import bug_reports


def test_get_bug_reports_dir_prefers_environment(monkeypatch):
    monkeypatch.setenv("BUG_REPORTS_PATH", "/tmp/from_env")

    def _sentinel():
        raise AssertionError("load_config should not be called when env override is set")

    monkeypatch.setattr(bug_reports, "load_config", _sentinel)

    assert bug_reports.get_bug_reports_dir() == "/tmp/from_env"

    monkeypatch.delenv("BUG_REPORTS_PATH")


def test_get_bug_reports_dir_uses_config_value(monkeypatch):
    monkeypatch.delenv("BUG_REPORTS_PATH", raising=False)

    monkeypatch.setattr(
        bug_reports,
        "load_config",
        lambda: {"bug_reports": {"storage_path": "/tmp/from_config"}},
    )

    assert bug_reports.get_bug_reports_dir() == "/tmp/from_config"


def test_get_bug_reports_dir_falls_back_when_config_errors(monkeypatch):
    monkeypatch.delenv("BUG_REPORTS_PATH", raising=False)

    def _raise():
        raise RuntimeError("boom")

    monkeypatch.setattr(bug_reports, "load_config", _raise)

    assert bug_reports.get_bug_reports_dir() == "/mnt/storage/imagineer/bug_reports"
