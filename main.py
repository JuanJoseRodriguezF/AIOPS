from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import pandas as pd
import io
from model import detect_anomalies, prepare_data_for_plot

app = FastAPI(title="AIOps Anomaly Detection API")

# Servir archivos estáticos (frontend)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def root():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/upload")
async def upload_csv(file: UploadFile = File(...)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")
    
    # Leer CSV
    contents = await file.read()
    try:
        df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading CSV: {str(e)}")
    
    # Verificar columnas necesarias
    required_cols = ['timestamp', 'cpu_usage', 'network_in_kb', 'packet_rate']
    for col in required_cols:
        if col not in df.columns:
            raise HTTPException(status_code=400, detail=f"Missing required column: {col}")
    
    # Detectar anomalías
    df_with_anomalies = detect_anomalies(df)
    
    # Preparar datos para visualización
    plot_data = prepare_data_for_plot(df_with_anomalies)
    
    return {"data": plot_data}

# Endpoint opcional para simular tiempo real (devuelve datos paginados)
@app.get("/realtime/{filename}")
async def realtime_stream(filename: str, start: int = 0, limit: int = 10):
    # Esta función espera que el archivo se haya guardado previamente
    # Para simplicidad, se puede implementar una caché en memoria.
    # En este ejemplo, se asume que el archivo se subió y se guardó temporalmente.
    # Sin embargo, lo dejamos como esqueleto para extensión.
    return {"message": "Realtime simulation not yet implemented"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)