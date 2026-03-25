from dataclasses import dataclass
from pathlib import Path
import os
from typing import Dict

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = BASE_DIR / "data" / "tracker.db"
DEFAULT_ROUTE_PATH = BASE_DIR / "static" / "data" / "route.geojson"


load_dotenv(ROOT_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    device_key: str
    device_keys: Dict[str, str]
    db_path: Path
    route_path: Path
    allowed_origin: str
    viewer_username: str
    viewer_password: str
    admin_username: str
    admin_password: str

    def key_for_device(self, device_id: str) -> str | None:
        if self.device_keys:
            return self.device_keys.get(device_id)
        return self.device_key if self.device_key else None

    @staticmethod
    def from_env() -> "Settings":
        device_keys = _parse_device_keys(os.getenv("DEVICE_KEYS", ""))
        return Settings(
            device_key=os.getenv("DEVICE_KEY", "replace-me").strip(),
            device_keys=device_keys,
            db_path=Path(os.getenv("DB_PATH", str(DEFAULT_DB_PATH))),
            route_path=Path(os.getenv("ROUTE_PATH", str(DEFAULT_ROUTE_PATH))),
            allowed_origin=os.getenv("ALLOWED_ORIGIN", "*"),
            viewer_username=os.getenv("VIEWER_USERNAME", "viewer"),
            viewer_password=os.getenv("VIEWER_PASSWORD", ""),
            admin_username=os.getenv("ADMIN_USERNAME", "admin"),
            admin_password=os.getenv("ADMIN_PASSWORD", "admin"),
        )


def _parse_device_keys(raw: str) -> Dict[str, str]:
    parsed: Dict[str, str] = {}
    for pair in raw.split(","):
        value = pair.strip()
        if not value or ":" not in value:
            continue
        device_id, key = value.split(":", 1)
        did = device_id.strip()
        dkey = key.strip()
        if did and dkey:
            parsed[did] = dkey
    return parsed

settings = Settings.from_env()
