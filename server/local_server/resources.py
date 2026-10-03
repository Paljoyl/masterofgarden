"""Use the Windows TW client's cached catalog version without scanning its assets."""
import os
from pathlib import Path
import re

from .protocol import LocalError


def catalog_hash_path():
    # Unity persistentDataPath for the supported SOFTSTAR Windows client.
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        raise LocalError("local_resource_catalog_missing", 503)
    return (Path(local_app_data).parent / "LocalLow" / "SOFTSTAR Games INC_" /
            "MasterofGarden" / "com.unity.addressables" / "catalog_0.0.0.hash")


def installed_resource_hashes():
    try:
        # Read only one tiny version file, never the catalog or bundle contents.
        with catalog_hash_path().open("rb") as source:
            raw = source.read(65)
        value = raw.decode("ascii").strip()
    except (OSError, UnicodeError) as exc:
        raise LocalError("local_resource_catalog_missing", 503) from exc
    if not re.fullmatch(r"[0-9a-fA-F]{32}", value):
        raise LocalError("local_resource_catalog_invalid", 503)
    return {"StandaloneWindows64_zh_TW": value.lower()}
