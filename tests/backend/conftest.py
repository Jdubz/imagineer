"""
Pytest configuration and fixtures for backend tests
"""

import gc
import os
import sys
import tempfile
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Configure unique database path per worker for pytest-xdist
worker_id = os.environ.get("PYTEST_XDIST_WORKER", "master")
os.environ["DATABASE_URL"] = f"sqlite:////tmp/imagineer_test_{worker_id}.db"

from server.api import app as flask_app  # noqa: E402


def _current_memory_mb() -> float:
    """Best-effort current RSS in MB."""
    try:
        with open("/proc/self/statm", "r", encoding="utf-8") as statm:
            rss_pages = int(statm.readline().split()[1])
        page_size = os.sysconf("SC_PAGE_SIZE")
        return rss_pages * page_size / (1024 * 1024)
    except Exception:
        import resource

        usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        if sys.platform == "darwin":
            return usage / (1024 * 1024)
        return usage / 1024


def _apply_process_memory_limit(limit_mb: float) -> bool:
    """Set an OS memory ceiling for the current process when possible."""
    try:
        import resource
    except ImportError:
        return False

    limit_bytes = int(limit_mb * 1024 * 1024)
    if limit_bytes <= 0:
        return False

    limit_consts = [
        getattr(resource, name) for name in ("RLIMIT_AS", "RLIMIT_DATA") if hasattr(resource, name)
    ]

    def enforce(limit_const: int) -> bool:
        try:
            soft, hard = resource.getrlimit(limit_const)
        except (ValueError, OSError):
            return False

        hard_is_infinite = hard in {0, resource.RLIM_INFINITY}
        target = min(limit_bytes, hard if not hard_is_infinite else limit_bytes)

        if soft <= target and (not hard_is_infinite and hard <= target):
            return True  # limit already active

        try:
            resource.setrlimit(limit_const, (target, target))
        except (ValueError, OSError):
            return False
        return True

    return any(enforce(limit_const) for limit_const in limit_consts)


def pytest_addoption(parser):
    parser.addoption(
        "--max-mem",
        action="store",
        default=None,
        help=(
            "Maximum resident memory in MB allowed for the pytest process. "
            "Can also be set via PYTEST_MAX_MEMORY_MB. Set to 0 to disable the guard."
        ),
    )


def pytest_configure(config):
    disable_guard = os.environ.get("PYTEST_DISABLE_MEMORY_GUARD", "").lower() in {
        "1",
        "true",
        "yes",
    }
    threshold_opt = config.getoption("--max-mem") or os.environ.get("PYTEST_MAX_MEMORY_MB")
    try:
        threshold_val = float(threshold_opt) if threshold_opt is not None else 8192.0
    except ValueError:
        threshold_val = 8192.0

    if threshold_val <= 0:
        disable_guard = True

    config._memory_guard_enabled = not disable_guard
    config._memory_guard_threshold = threshold_val
    config._memory_guard_os_limit = False
    config._memory_guard_records = []
    config._memory_guard_baseline = _current_memory_mb()

    reporter = config.pluginmanager.get_plugin("terminalreporter")
    if reporter and config._memory_guard_enabled:
        if _apply_process_memory_limit(threshold_val):
            config._memory_guard_os_limit = True
            reporter.write_line(
                f"[memory-guard] Applied RLIMIT cap at ~{threshold_val:.1f} MB of address space"
            )
        else:
            reporter.write_line(
                "[memory-guard] OS-level limit unavailable; relying on RSS monitoring only"
            )

        reporter.write_line(
            f"[memory-guard] Baseline RSS: {config._memory_guard_baseline:.1f} MB | "
            f"Threshold: {config._memory_guard_threshold:.1f} MB"
        )


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    config = item.config
    if not getattr(config, "_memory_guard_enabled", False):
        yield
        return

    start = _current_memory_mb()
    yield
    gc.collect()
    end = _current_memory_mb()

    records = getattr(config, "_memory_guard_records", None)
    if records is not None:
        records.append((end, end - start, item.nodeid))

    threshold = getattr(config, "_memory_guard_threshold", float("inf"))
    if end > threshold:
        pytest.fail(
            (
                f"Memory budget exceeded after {item.nodeid}: "
                f"{end:.1f} MB RSS (limit {threshold:.1f} MB). "
                "Set PYTEST_MAX_MEMORY_MB/--max-mem to adjust or "
                "PYTEST_DISABLE_MEMORY_GUARD=1 to disable."
            ),
            pytrace=False,
        )


def pytest_sessionfinish(session, exitstatus):
    config = session.config
    if not getattr(config, "_memory_guard_enabled", False):
        return

    reporter = config.pluginmanager.get_plugin("terminalreporter")
    if not reporter:
        return

    records = getattr(config, "_memory_guard_records", [])
    if not records:
        return

    peak_record = max(records, key=lambda entry: entry[0])
    if getattr(config, "_memory_guard_os_limit", False) and reporter:
        reporter.write_line("[memory-guard] OS-level cap was active during this run.")
    reporter.write_line(f"[memory-guard] Peak RSS: {peak_record[0]:.1f} MB during {peak_record[2]}")
    reporter.write_line("[memory-guard] Top 5 tests by RSS delta:")
    for idx, (rss, delta, nodeid) in enumerate(
        sorted(records, key=lambda entry: entry[1], reverse=True)[:5], start=1
    ):
        reporter.write_line(f"  {idx}. {nodeid} | Δ {delta:+.2f} MB | RSS {rss:.1f} MB")


@pytest.fixture
def app():
    """Create and configure a test Flask app instance"""
    # Use a temporary database for tests
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
        test_db_path = tmp_db.name

    flask_app.config.update(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{test_db_path}",
        }
    )

    # Recreate database with current schema
    from server.database import db

    with flask_app.app_context():
        db.drop_all()
        db.create_all()

    try:
        yield flask_app
    finally:
        from server.database import db as _db_cleanup

        with flask_app.app_context():
            _db_cleanup.session.remove()
        try:
            os.unlink(test_db_path)
        except OSError:
            pass
        gc.collect()


@pytest.fixture
def client(app):
    """A test client for the app"""
    return app.test_client()


@pytest.fixture
def admin_client(client):
    """Return a test client with an authenticated admin session."""
    from server.routes import generation as generation_module

    with client.session_transaction() as session:
        session["_user_id"] = "admin@example.com"
        session["_fresh"] = True
        session["user"] = {
            "email": "admin@example.com",
            "name": "Test Admin",
            "picture": "",
            "role": "admin",
        }

    with generation_module._generation_rate_lock:
        generation_module._generation_request_times.clear()

    return client


@pytest.fixture
def runner(app):
    """A test runner for the app's Click commands"""
    return app.test_cli_runner()


@pytest.fixture
def temp_config():
    """Create a temporary config file for testing"""
    config_data = {
        "model": {
            "default": "runwayml/stable-diffusion-v1-5",
            "cache_dir": "/tmp/imagineer/models",
        },
        "outputs": {"base_dir": "/tmp/imagineer/outputs"},
        "output": {"directory": "/tmp/imagineer/outputs", "format": "png", "save_metadata": True},
        "generation": {
            "width": 512,
            "height": 512,
            "steps": 25,
            "guidance_scale": 7.5,
            "negative_prompt": "test negative prompt",
            "batch_size": 1,
            "num_images": 1,
        },
        "training": {
            "learning_rate": 0.0001,
            "checkpoint_dir": "/tmp/imagineer/checkpoints",
            "lora": {"rank": 4, "alpha": 4, "dropout": 0.1},
            "batch_size": 1,
            "gradient_accumulation_steps": 4,
        },
        "sets": {"directory": "/tmp/imagineer/sets"},
        "dataset": {"data_dir": "/tmp/imagineer/data/training"},
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config_data, f)
        temp_path = f.name

    yield temp_path

    # Cleanup
    Path(temp_path).unlink(missing_ok=True)


@pytest.fixture
def temp_output_dir():
    """Create a temporary output directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_job_data():
    """Sample job data for testing"""
    return {
        "prompt": "a beautiful landscape",
        "seed": 42,
        "steps": 25,
        "width": 512,
        "height": 512,
        "guidance_scale": 7.5,
        "negative_prompt": "blurry, low quality",
    }


@pytest.fixture
def mock_admin_auth():
    """Mock admin authentication"""
    # Create a mock admin user
    admin_user = MagicMock()
    admin_user.email = "admin@test.com"
    admin_user.name = "Admin User"
    admin_user.picture = ""
    admin_user.role = "admin"
    admin_user.is_authenticated = True
    admin_user.is_admin.return_value = True

    patch_targets = [
        "server.auth.current_user",
        "server.routes.images.current_user",
        "server.routes.albums.current_user",
        "server.routes.training.current_user",
        "server.routes.scraping.current_user",
        "server.routes.scraping_simple.current_user",
        "server.routes.admin.current_user",
        "server.routes.admin.current_user",
    ]

    with ExitStack() as stack:
        for target in patch_targets:
            try:
                stack.enter_context(patch(target, admin_user, create=True))
            except ModuleNotFoundError:
                continue
        yield admin_user


@pytest.fixture
def mock_public_auth():
    """Mock public user authentication"""
    # Create a mock public user
    public_user = MagicMock()
    public_user.email = "public@test.com"
    public_user.name = "Public User"
    public_user.picture = ""
    public_user.role = None
    public_user.is_authenticated = True
    public_user.is_admin.return_value = False

    patch_targets = [
        "server.auth.current_user",
        "server.routes.images.current_user",
        "server.routes.albums.current_user",
        "server.routes.training.current_user",
        "server.routes.scraping.current_user",
    ]

    with ExitStack() as stack:
        for target in patch_targets:
            try:
                stack.enter_context(patch(target, public_user))
            except ModuleNotFoundError:
                continue
        yield public_user


@pytest.fixture
def generation_paths(tmp_path, monkeypatch):
    """Provide isolated directories and config for generation route tests."""
    from server.routes import generation as generation_module

    base_dir = tmp_path / "imagineer"
    output_dir = base_dir / "outputs"
    lora_dir = base_dir / "models" / "lora"
    output_dir.mkdir(parents=True, exist_ok=True)
    lora_dir.mkdir(parents=True, exist_ok=True)

    config = {
        "output": {"directory": str(output_dir)},
        "model": {"cache_dir": str(base_dir / "models")},
    }

    monkeypatch.setattr(generation_module, "load_config", lambda: config)
    return {"output_dir": output_dir, "lora_dir": lora_dir, "config": config}


@pytest.fixture(autouse=True)
def setup_test_directories():
    """Ensure test directories exist and are writable"""
    import os
    from pathlib import Path

    # Create test directories
    test_dirs = [
        "/tmp/imagineer/outputs/uploads",
        "/tmp/imagineer/outputs/thumbnails",
        "/tmp/imagineer/models/lora",
        "/tmp/imagineer/checkpoints",
        "/tmp/imagineer/sets",
        "/tmp/imagineer/data/training",
    ]

    for dir_path in test_dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        # Ensure directory is writable
        os.chmod(dir_path, 0o755)

    yield

    # Cleanup after tests
    import shutil

    try:
        shutil.rmtree("/tmp/imagineer", ignore_errors=True)
    except Exception:
        pass
