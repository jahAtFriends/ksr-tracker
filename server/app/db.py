from __future__ import annotations

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
        CREATE INDEX IF NOT EXISTS idx_location_points_ts
        ON location_points (session_id, ts_utc)
        """
    )
    conn.commit()
    conn.close()


def insert_points(session_id: str, batch_id: str | None, rows: list[dict[str, Any]]) -> int:
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
                WHERE session_id = ? AND batch_id = ? AND ts_utc = ? AND lat = ? AND lng = ?
                LIMIT 1
                """,
                (session_id, batch_id, row["ts_utc"], row["lat"], row["lng"]),
            ).fetchone()
            if existing:
                continue
        cur.execute(
            """
            INSERT INTO location_points
            (session_id, batch_id, lat, lng, acc, speed, ts_utc, received_utc)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
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
        SELECT id, session_id, lat, lng, acc, speed, ts_utc, received_utc
        FROM location_points
        WHERE session_id = ?
        ORDER BY ts_utc DESC
        LIMIT 1
        """,
        (session_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_recent_points(session_id: str, limit: int = 200) -> list[dict[str, Any]]:
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT id, session_id, lat, lng, acc, speed, ts_utc, received_utc
        FROM location_points
        WHERE session_id = ?
        ORDER BY ts_utc DESC
        LIMIT ?
        """,
        (session_id, limit),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]
