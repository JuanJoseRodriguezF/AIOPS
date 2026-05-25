from __future__ import annotations

import io

import pandas as pd
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from database import (
    clear_all_data,
    create_analysis_run,
    get_analysis_run,
    init_db,
    insert_alerts,
    insert_observations,
    list_alerts,
    list_analysis_runs,
)
from model import (
    DEFAULT_CONTAMINATION,
    MODEL_NAME,
    build_alerts,
    calculate_metrics,
    detect_anomalies,
    prepare_data_for_plot,
    summarize_labels,
)

app = FastAPI(
    title="AIOps Observability API",
    description="API para detección automática de anomalías, persistencia de análisis y alertamiento operacional.",
    version="2.0.0",
)

app.mount("/static", StaticFiles(directory="static"), name="static")

# Garantiza que la base exista tanto en ejecución normal como en pruebas.
init_db()


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/", response_class=HTMLResponse)
async def root():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "AIOps Observability API", "database": "sqlite"}


@app.post("/upload")
async def upload_csv(
    file: UploadFile = File(...),
    contamination: float = Query(DEFAULT_CONTAMINATION, ge=0.001, le=0.5),
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Solo se permiten archivos CSV")

    contents = await file.read()
    try:
        df = pd.read_csv(io.StringIO(contents.decode("utf-8")))
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(io.StringIO(contents.decode("latin-1")))
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Error leyendo CSV: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Error leyendo CSV: {exc}") from exc

    try:
        df_with_anomalies, features = detect_anomalies(df, contamination=contamination)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    records = prepare_data_for_plot(df_with_anomalies)
    metrics = calculate_metrics(records)
    label_summary = summarize_labels(df)

    run_id = create_analysis_run(
        filename=file.filename,
        model_name=MODEL_NAME,
        contamination=contamination,
        features=features,
        total_records=metrics["total_records"],
        anomaly_count=metrics["anomaly_count"],
        true_label_summary=label_summary,
    )
    observation_ids = insert_observations(run_id, records)
    alerts = build_alerts(records, observation_ids)
    insert_alerts(run_id, alerts)

    return {
        "run_id": run_id,
        "model": MODEL_NAME,
        "contamination": contamination,
        "features": features,
        "metrics": metrics,
        "label_summary": label_summary,
        "alerts": alerts[:20],
        "data": records,
    }


@app.get("/analyses")
async def analyses(limit: int = Query(30, ge=1, le=100)):
    return {"items": list_analysis_runs(limit=limit)}


@app.get("/analyses/{run_id}")
async def analysis_detail(run_id: int):
    run = get_analysis_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Análisis no encontrado")
    return run


@app.get("/alerts")
async def alerts(limit: int = Query(50, ge=1, le=200)):
    return {"items": list_alerts(limit=limit)}


@app.delete("/analyses")
async def delete_analyses():
    clear_all_data()
    return {"message": "Historial eliminado correctamente"}


@app.get("/realtime/simulated")
async def realtime_simulated(run_id: int, start: int = 0, limit: int = Query(25, ge=1, le=200)):
    """Simulación gratuita de tiempo real usando registros ya persistidos."""
    run = get_analysis_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Análisis no encontrado")
    data = run.get("observations", [])
    chunk = data[start : start + limit]
    next_start = start + len(chunk)
    return {
        "run_id": run_id,
        "start": start,
        "limit": limit,
        "next_start": next_start,
        "has_more": next_start < len(data),
        "data": chunk,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
