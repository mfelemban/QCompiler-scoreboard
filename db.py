from __future__ import annotations

import sqlite3
from pathlib import Path

DEFAULT_WEIGHTS = {"w1": 10.0, "w2": 1.0, "w3": 1.0}


def init_db(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_name TEXT NOT NULL,
            submitted_at TEXT NOT NULL,
            qubit_count INTEGER NOT NULL,
            depth INTEGER NOT NULL,
            gate_count INTEGER NOT NULL,
            score REAL NOT NULL,
            w1 REAL NOT NULL,
            w2 REAL NOT NULL,
            w3 REAL NOT NULL,
            filename TEXT,
            circuit_text TEXT,
            verified INTEGER NOT NULL,
            verify_message TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )
    for k, v in DEFAULT_WEIGHTS.items():
        conn.execute(
            "INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)", (k, str(v))
        )
    conn.commit()
    return conn


def get_weights(conn: sqlite3.Connection) -> dict:
    rows = conn.execute(
        "SELECT key, value FROM config WHERE key IN ('w1','w2','w3')"
    ).fetchall()
    return {r["key"]: float(r["value"]) for r in rows}


def set_weights(conn: sqlite3.Connection, w1: float, w2: float, w3: float) -> None:
    for k, v in (("w1", w1), ("w2", w2), ("w3", w3)):
        conn.execute("UPDATE config SET value=? WHERE key=?", (str(v), k))
    conn.commit()


def insert_submission(conn: sqlite3.Connection, **kwargs) -> int:
    cols = ", ".join(kwargs.keys())
    placeholders = ", ".join("?" * len(kwargs))
    cursor = conn.execute(
        f"INSERT INTO submissions ({cols}) VALUES ({placeholders})",
        tuple(kwargs.values()),
    )
    conn.commit()
    return cursor.lastrowid


def best_per_team(conn: sqlite3.Connection):
    return conn.execute(
        """
        WITH ranked AS (
            SELECT *,
                   ROW_NUMBER() OVER (
                       PARTITION BY team_name
                       ORDER BY score ASC, submitted_at ASC
                   ) AS rn
            FROM submissions
            WHERE verified = 1
        )
        SELECT * FROM ranked WHERE rn = 1 ORDER BY score ASC, submitted_at ASC
        """
    ).fetchall()


def all_submissions(conn: sqlite3.Connection):
    return conn.execute(
        "SELECT * FROM submissions ORDER BY submitted_at DESC"
    ).fetchall()


def set_verified(conn: sqlite3.Connection, submission_id: int, verified: bool) -> None:
    conn.execute(
        "UPDATE submissions SET verified=? WHERE id=?",
        (1 if verified else 0, submission_id),
    )
    conn.commit()


def delete_submission(conn: sqlite3.Connection, submission_id: int) -> None:
    conn.execute("DELETE FROM submissions WHERE id = ?", (submission_id,))
    conn.commit()


def rescore_all(conn: sqlite3.Connection, w1: float, w2: float, w3: float) -> None:
    conn.execute(
        "UPDATE submissions SET w1=?, w2=?, w3=?, "
        "score = ?*qubit_count + ?*depth + ?*gate_count",
        (w1, w2, w3, w1, w2, w3),
    )
    conn.commit()
