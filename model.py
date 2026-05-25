from __future__ import annotations

import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

MODEL_NAME = "Isolation Forest"
DEFAULT_CONTAMINATION = 0.05

# Métricas operativas y de seguridad disponibles en los CSV del caso de uso.
CANDIDATE_FEATURES = [
    "cpu_usage",
    "memory_usage",
    "network_in_kb",
    "network_out_kb",
    "packet_rate",
    "avg_response_time_ms",
    "service_access_count",
    "failed_auth_attempts",
    "is_encrypted",
    "geo_location_variation",
]

REQUIRED_COLUMNS = ["timestamp", "cpu_usage", "network_in_kb", "packet_rate"]


def validate_input(df: pd.DataFrame) -> None:
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError("Faltan columnas requeridas: " + ", ".join(missing))


def available_features(df: pd.DataFrame) -> list[str]:
    return [col for col in CANDIDATE_FEATURES if col in df.columns]


def detect_anomalies(df: pd.DataFrame, contamination: float = DEFAULT_CONTAMINATION) -> tuple[pd.DataFrame, list[str]]:
    """
    Detecta anomalías con Isolation Forest.

    Retorna un DataFrame con:
    - anomaly: -1 anomalía, 1 normal
    - is_anomaly: booleano
    - anomaly_score: mayor valor = mayor riesgo relativo
    """
    validate_input(df)
    data = df.copy()
    features = available_features(data)

    if len(features) < 2:
        raise ValueError("Se necesitan al menos dos métricas numéricas para detectar anomalías.")

    # Convertir métricas a numérico y rellenar faltantes con mediana.
    X = data[features].apply(pd.to_numeric, errors="coerce")
    X = X.fillna(X.median(numeric_only=True)).fillna(0)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    iso_forest = IsolationForest(
        contamination=contamination,
        random_state=42,
        n_estimators=200,
    )
    predictions = iso_forest.fit_predict(X_scaled)

    # score_samples: menor = más anómalo. Lo invertimos para lectura tipo riesgo.
    risk_scores = -iso_forest.score_samples(X_scaled)

    data["anomaly"] = predictions
    data["is_anomaly"] = predictions == -1
    data["anomaly_score"] = risk_scores.round(6)
    return data, features


def prepare_data_for_plot(df: pd.DataFrame) -> list[dict]:
    """Convierte DataFrame a JSON para frontend y persistencia."""
    data = df.copy()
    data["timestamp"] = pd.to_datetime(data["timestamp"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")

    columns = [
        "timestamp",
        "device_id",
        "device_type",
        "cpu_usage",
        "memory_usage",
        "network_in_kb",
        "network_out_kb",
        "packet_rate",
        "avg_response_time_ms",
        "service_access_count",
        "failed_auth_attempts",
        "is_encrypted",
        "geo_location_variation",
        "label",
        "anomaly",
        "is_anomaly",
        "anomaly_score",
    ]
    existing_columns = [col for col in columns if col in data.columns]
    return data[existing_columns].to_dict(orient="records")


def summarize_labels(df: pd.DataFrame) -> dict[str, int]:
    if "label" not in df.columns:
        return {}
    return {str(k): int(v) for k, v in df["label"].value_counts().to_dict().items()}


def calculate_metrics(records: list[dict]) -> dict:
    total = len(records)
    anomaly_count = sum(1 for item in records if item.get("is_anomaly"))
    avg_cpu = _avg(records, "cpu_usage")
    avg_memory = _avg(records, "memory_usage")
    avg_response = _avg(records, "avg_response_time_ms")
    failed_auth = sum(float(item.get("failed_auth_attempts") or 0) for item in records)
    return {
        "total_records": total,
        "anomaly_count": anomaly_count,
        "normal_count": total - anomaly_count,
        "anomaly_pct": round((anomaly_count / total * 100) if total else 0, 2),
        "avg_cpu": round(avg_cpu, 2),
        "avg_memory": round(avg_memory, 2),
        "avg_response_time_ms": round(avg_response, 2),
        "failed_auth_attempts_total": int(failed_auth),
    }


def build_alerts(records: list[dict], observation_ids: list[int] | None = None) -> list[dict]:
    """Genera alertas explicables para el dashboard NOC/SOC."""
    alerts: list[dict] = []
    observation_ids = observation_ids or [None] * len(records)

    for row, observation_id in zip(records, observation_ids):
        if not row.get("is_anomaly"):
            continue

        checks = [
            ("CPU", "cpu_usage", 85, "high"),
            ("Memoria", "memory_usage", 85, "high"),
            ("Tráfico entrante", "network_in_kb", 1400, "medium"),
            ("Tráfico saliente", "network_out_kb", 1400, "medium"),
            ("Paquetes", "packet_rate", 900, "medium"),
            ("Tiempo de respuesta", "avg_response_time_ms", 500, "high"),
            ("Intentos fallidos", "failed_auth_attempts", 8, "critical"),
            ("Variación geográfica", "geo_location_variation", 25, "critical"),
        ]
        triggered = []
        severity = "medium"
        for label, field, threshold, sev in checks:
            value = row.get(field)
            try:
                if value is not None and float(value) >= threshold:
                    triggered.append(f"{label}: {value}")
                    if sev == "critical":
                        severity = "critical"
                    elif sev == "high" and severity != "critical":
                        severity = "high"
            except Exception:
                pass

        metric = ", ".join(triggered) if triggered else "Patrón multivariable fuera de línea base"
        device = row.get("device_id") or "dispositivo no identificado"
        timestamp = row.get("timestamp") or "sin timestamp"
        alerts.append(
            {
                "observation_id": observation_id,
                "severity": severity,
                "title": f"Anomalía detectada en {device}",
                "description": f"{timestamp} · {metric}",
                "metric": metric,
            }
        )

    return alerts[:100]


def _avg(records: list[dict], field: str) -> float:
    vals = []
    for item in records:
        try:
            if item.get(field) is not None:
                vals.append(float(item[field]))
        except Exception:
            pass
    return sum(vals) / len(vals) if vals else 0.0
