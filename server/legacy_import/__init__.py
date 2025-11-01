"""
Helpers for migrating legacy image assets into the Imagineer database.

This package contains three layers:
1. Collectors - read legacy storage to produce normalized records.
2. Stagers - copy/symlink legacy assets into the repo's canonical staging area.
3. Importers (future) - persist staged assets into the database & albums.
"""

from .collectors import collect_legacy_outputs  # noqa: F401
from .importer import import_records  # noqa: F401
from .models import LegacyAlbum, LegacyImageRecord  # noqa: F401
