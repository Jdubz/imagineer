import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


def safe_remove_path(path: Path) -> bool:
    if not path:
        return False

    try:
        if path.is_dir():
            shutil.rmtree(path)
        elif path.is_file():
            path.unlink()
        else:
            return False
        return True
    except Exception as exc:  # pragma: no cover - best effort cleanup
        logger.warning("Failed to remove artifact at %s: %s", path, exc, exc_info=True)
