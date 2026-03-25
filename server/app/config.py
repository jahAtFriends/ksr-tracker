from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = BASE_DIR / "data" / "tracker.db"
DEFAULT_ROUTE_PATH = BASE_DIR / "static" / "data" / "route.geojson"


load_dotenv(ROOT_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    device_key: str
    db_path: Path
    route_path: Path
    allowed_origin: str
    viewer_username: str
    viewer_password: str

    @staticmethod
    def from_env() -> "Settings":
        return Settings(
            device_key=os.getenv("DEVICE_KEY", "replace-me").strip(),
            db_path=Path(os.getenv("DB_PATH", str(DEFAULT_DB_PATH))),
            route_path=Path(os.getenv("ROUTE_PATH", str(DEFAULT_ROUTE_PATH))),
            allowed_origin=os.getenv("ALLOWED_ORIGIN", "*"),
            viewer_username=os.getenv("VIEWER_USERNAME", "viewer"),
            viewer_password=os.getenv("VIEWER_PASSWORD", ""),
        )


settings = Settings.from_env()
