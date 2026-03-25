from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .config import settings


def _ensure_db_parent() -> None:
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)


def get_connection() -> sqlite3.Connection:
    _ensure_db_parent()
    conn = sqlite3.connect(str(settings.db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS location_points (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            device_id TEXT NOT NULL DEFAULT 'tracker-1',
            batch_id TEXT,
            lat REAL NOT NULL,
            lng REAL NOT NULL,
            acc REAL,
            speed REAL,
            ts_utc TEXT NOT NULL,
            received_utc TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS route_points (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seq INTEGER NOT NULL,
            lat REAL NOT NULL,
            lng REAL NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS trackers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL UNIQUE,
            device_key TEXT NOT NULL,
            created_utc TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_location_points_ts
        ON location_points (session_id, ts_utc)
        """
    )
    cols = cur.execute("PRAGMA table_info(location_points)").fetchall()
    col_names = {row[1] for row in cols}
    if "device_id" not in col_names:
        cur.execute(
            """
            ALTER TABLE location_points
            ADD COLUMN device_id TEXT NOT NULL DEFAULT 'tracker-1'
            """
        )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_location_points_device
        ON location_points (session_id, device_id, ts_utc)
        """
    )

    tracker_count = cur.execute("SELECT COUNT(*) FROM trackers").fetchone()[0]
    if tracker_count == 0:
        seeded = False
        for device_id, device_key in settings.device_keys.items():
            cur.execute(
                "INSERT OR IGNORE INTO trackers (device_id, device_key) VALUES (?, ?)",
                (device_id, device_key),
            )
            seeded = True
        if not seeded and settings.device_key:
            cur.execute(
                "INSERT OR IGNORE INTO trackers (device_id, device_key) VALUES (?, ?)",
                ("tracker-1", settings.device_key),
            )

    conn.commit()
    conn.close()


def list_trackers(include_keys: bool = False) -> list[dict[str, Any]]:
    conn = get_connection()
    if include_keys:
        rows = conn.execute(
            """
            SELECT device_id, device_key, created_utc
            FROM trackers
            ORDER BY device_id ASC
            """
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT device_id, created_utc
            FROM trackers
            ORDER BY device_id ASC
            """
        ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_device_key(device_id: str) -> str | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT device_key FROM trackers WHERE device_id = ? LIMIT 1",
        (device_id,),
    ).fetchone()
    conn.close()
    if row:
        return str(row["device_key"])
    return settings.key_for_device(device_id)


def upsert_tracker(device_id: str, device_key: str) -> None:
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO trackers (device_id, device_key)
        VALUES (?, ?)
        ON CONFLICT(device_id) DO UPDATE SET device_key = excluded.device_key
        """,
        (device_id, device_key),
    )
    conn.commit()
    conn.close()


def delete_tracker(device_id: str) -> bool:
    conn = get_connection()
    cur = conn.execute("DELETE FROM trackers WHERE device_id = ?", (device_id,))
    conn.commit()
    conn.close()
    return cur.rowcount > 0


def write_route_geojson(route_geojson: dict[str, Any]) -> None:
    settings.route_path.parent.mkdir(parents=True, exist_ok=True)
    settings.route_path.write_text(json.dumps(route_geojson), encoding="utf-8")


def clear_location_points() -> int:
    conn = get_connection()
    cur = conn.execute("DELETE FROM location_points")
    conn.commit()
    conn.close()
    return cur.rowcount


def insert_points(session_id: str, device_id: str, batch_id: str | None, rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    conn = get_connection()
    cur = conn.cursor()
    inserted = 0
    for row in rows:
        if batch_id:
            existing = cur.execute(
                """
                SELECT 1 FROM location_points
                WHERE session_id = ? AND device_id = ? AND batch_id = ? AND ts_utc = ? AND lat = ? AND lng = ?
                LIMIT 1
                """,
                (session_id, device_id, batch_id, row["ts_utc"], row["lat"], row["lng"]),
            ).fetchone()
            if existing:
                continue
        cur.execute(
            """
            INSERT INTO location_points
            (session_id, device_id, batch_id, lat, lng, acc, speed, ts_utc, received_utc)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                device_id,
                batch_id,
                row["lat"],
                row["lng"],
                row.get("acc"),
                row.get("speed"),
                row["ts_utc"],
                row["received_utc"],
            ),
        )
        inserted += 1
    conn.commit()
    conn.close()
    return inserted


def get_latest_point(session_id: str) -> dict[str, Any] | None:
    conn = get_connection()
    row = conn.execute(
        """
        SELECT id, session_id, device_id, lat, lng, acc, speed, ts_utc, received_utc
        FROM location_points
        WHERE session_id = ?
        ORDER BY ts_utc DESC
        LIMIT 1
        """,
        (session_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_latest_points_by_device(session_id: str) -> list[dict[str, Any]]:
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT p.id, p.session_id, p.device_id, p.lat, p.lng, p.acc, p.speed, p.ts_utc, p.received_utc
        FROM location_points p
        INNER JOIN (
            SELECT session_id, device_id, MAX(ts_utc) AS max_ts
            FROM location_points
            WHERE session_id = ?
            GROUP BY session_id, device_id
        ) latest
        ON p.session_id = latest.session_id
        AND p.device_id = latest.device_id
        AND p.ts_utc = latest.max_ts
        WHERE p.session_id = ?
        ORDER BY p.device_id ASC
        """,
        (session_id, session_id),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_recent_points(session_id: str, limit: int = 200) -> list[dict[str, Any]]:
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT id, session_id, device_id, lat, lng, acc, speed, ts_utc, received_utc
        FROM location_points
        WHERE session_id = ?
        ORDER BY ts_utc DESC
        LIMIT ?
        """,
        (session_id, limit),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]
