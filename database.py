"""Capa de persistencia local para el prototipo AIOps.

Se usa SQLite porque no requiere servidor, cuentas, pagos ni servicios externos.
La estructura deja el camino abierto para migrar a PostgreSQL en producción.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

DB_PATH = Path(__file__).resolve().parent / "data" / "aiops_observability.db"


def _now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        if value != value:  # NaN
            return None
        return float(value)
    except Exception:
        return None


def _safe_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        if value != value:  # NaN
            return None
        return int(value)
    except Exception:
        return None


@contextmanager
def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Crea las tablas si no existen."""
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS analysis_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                uploaded_at TEXT NOT NULL,
                model_name TEXT NOT NULL,
                contamination REAL NOT NULL,
                features_json TEXT NOT NULL,
                total_records INTEGER NOT NULL,
                anomaly_count INTEGER NOT NULL,
                anomaly_pct REAL NOT NULL,
                normal_count INTEGER NOT NULL,
                true_label_summary TEXT,
                status TEXT NOT NULL DEFAULT 'completed'
            );

            CREATE TABLE IF NOT EXISTS observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                timestamp TEXT,
                device_id TEXT,
                device_type TEXT,
                cpu_usage REAL,
                memory_usage REAL,
                network_in_kb REAL,
                network_out_kb REAL,
                packet_rate REAL,
                avg_response_time_ms REAL,
                service_access_count REAL,
                failed_auth_attempts REAL,
                is_encrypted INTEGER,
                geo_location_variation REAL,
                label TEXT,
                anomaly INTEGER NOT NULL,
                is_anomaly INTEGER NOT NULL,
                anomaly_score REAL,
                FOREIGN KEY(run_id) REFERENCES analysis_runs(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                observation_id INTEGER,
                created_at TEXT NOT NULL,
                severity TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                metric TEXT NOT NULL,
                acknowledged INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(run_id) REFERENCES analysis_runs(id) ON DELETE CASCADE,
                FOREIGN KEY(observation_id) REFERENCES observations(id) ON DELETE SET NULL
            );

            CREATE INDEX IF NOT EXISTS idx_observations_run_id ON observations(run_id);
            CREATE INDEX IF NOT EXISTS idx_observations_timestamp ON observations(timestamp);
            CREATE INDEX IF NOT EXISTS idx_alerts_run_id ON alerts(run_id);
            """
        )


def create_analysis_run(
    *,
    filename: str,
    model_name: str,
    contamination: float,
    features: list[str],
    total_records: int,
    anomaly_count: int,
    true_label_summary: dict[str, int] | None,
) -> int:
    normal_count = total_records - anomaly_count
    anomaly_pct = (anomaly_count / total_records * 100) if total_records else 0
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO analysis_runs (
                filename, uploaded_at, model_name, contamination, features_json,
                total_records, anomaly_count, anomaly_pct, normal_count,
                true_label_summary, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'completed')
            """,
            (
                filename,
                _now_iso(),
                model_name,
                contamination,
                json.dumps(features, ensure_ascii=False),
                total_records,
                anomaly_count,
                anomaly_pct,
                normal_count,
                json.dumps(true_label_summary or {}, ensure_ascii=False),
            ),
        )
        return int(cursor.lastrowid)


def insert_observations(run_id: int, records: Iterable[dict[str, Any]]) -> list[int]:
    """Inserta observaciones y retorna sus IDs en el mismo orden."""
    observation_ids: list[int] = []
    with get_connection() as conn:
        for row in records:
            cursor = conn.execute(
                """
                INSERT INTO observations (
                    run_id, timestamp, device_id, device_type, cpu_usage, memory_usage,
                    network_in_kb, network_out_kb, packet_rate, avg_response_time_ms,
                    service_access_count, failed_auth_attempts, is_encrypted,
                    geo_location_variation, label, anomaly, is_anomaly, anomaly_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    row.get("timestamp"),
                    row.get("device_id"),
                    row.get("device_type"),
                    _safe_float(row.get("cpu_usage")),
                    _safe_float(row.get("memory_usage")),
                    _safe_float(row.get("network_in_kb")),
                    _safe_float(row.get("network_out_kb")),
                    _safe_float(row.get("packet_rate")),
                    _safe_float(row.get("avg_response_time_ms")),
                    _safe_float(row.get("service_access_count")),
                    _safe_float(row.get("failed_auth_attempts")),
                    _safe_int(row.get("is_encrypted")),
                    _safe_float(row.get("geo_location_variation")),
                    row.get("label"),
                    _safe_int(row.get("anomaly")) or 1,
                    1 if row.get("is_anomaly") else 0,
                    _safe_float(row.get("anomaly_score")),
                ),
            )
            observation_ids.append(int(cursor.lastrowid))
    return observation_ids


def insert_alerts(run_id: int, alerts: Iterable[dict[str, Any]]) -> None:
    with get_connection() as conn:
        conn.executemany(
            """
            INSERT INTO alerts (
                run_id, observation_id, created_at, severity, title, description, metric, acknowledged
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 0)
            """,
            [
                (
                    run_id,
                    alert.get("observation_id"),
                    _now_iso(),
                    alert.get("severity", "medium"),
                    alert.get("title", "Anomalía detectada"),
                    alert.get("description", "Evento anómalo identificado por el modelo."),
                    alert.get("metric", "multiple"),
                )
                for alert in alerts
            ],
        )


def list_analysis_runs(limit: int = 30) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, filename, uploaded_at, model_name, contamination, total_records,
                   anomaly_count, anomaly_pct, normal_count, true_label_summary, status
            FROM analysis_runs
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def get_analysis_run(run_id: int, limit_observations: int = 10000) -> dict[str, Any] | None:
    with get_connection() as conn:
        run = conn.execute(
            "SELECT * FROM analysis_runs WHERE id = ?",
            (run_id,),
        ).fetchone()
        if not run:
            return None
        observations = conn.execute(
            """
            SELECT * FROM observations
            WHERE run_id = ?
            ORDER BY timestamp ASC, id ASC
            LIMIT ?
            """,
            (run_id, limit_observations),
        ).fetchall()
        alerts = conn.execute(
            """
            SELECT * FROM alerts
            WHERE run_id = ?
            ORDER BY id DESC
            LIMIT 50
            """,
            (run_id,),
        ).fetchall()

    result = _row_to_dict(run)
    result["features"] = json.loads(result.pop("features_json") or "[]")
    result["true_label_summary"] = json.loads(result.get("true_label_summary") or "{}")
    result["observations"] = [_row_to_dict(row) for row in observations]
    result["alerts"] = [_row_to_dict(row) for row in alerts]
    return result


def list_alerts(limit: int = 50) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT a.id, a.run_id, r.filename, a.created_at, a.severity, a.title,
                   a.description, a.metric, a.acknowledged
            FROM alerts a
            JOIN analysis_runs r ON r.id = a.run_id
            ORDER BY a.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def clear_all_data() -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM alerts")
        conn.execute("DELETE FROM observations")
        conn.execute("DELETE FROM analysis_runs")


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    if "is_anomaly" in data:
        data["is_anomaly"] = bool(data["is_anomaly"])
    if "acknowledged" in data:
        data["acknowledged"] = bool(data["acknowledged"])
    return data
