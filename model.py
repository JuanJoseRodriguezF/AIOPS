import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

def detect_anomalies(df: pd.DataFrame):
    """
    Detect anomalies using Isolation Forest.
    Input df must contain columns: cpu_usage, network_in_kb, packet_rate.
    Returns a copy of df with an 'anomaly' column (-1 for anomaly, 1 for normal).
    """
    # Seleccionar características
    features = ['cpu_usage', 'network_in_kb', 'packet_rate']
    X = df[features].copy()
    
    # Normalizar
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Entrenar Isolation Forest
    iso_forest = IsolationForest(contamination=0.05, random_state=42)
    predictions = iso_forest.fit_predict(X_scaled)
    
    # Añadir columna de anomalía (-1 = anomalía, 1 = normal)
    df['anomaly'] = predictions
    return df

def prepare_data_for_plot(df: pd.DataFrame):
    """Convierte DataFrame a formato JSON para el frontend."""
    # Asegurar que timestamp sea string ISO
    df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
    # Seleccionar columnas de interés
    plot_data = df[['timestamp', 'cpu_usage', 'network_in_kb', 'packet_rate', 'anomaly']].copy()
    # Convertir anomaly a booleano para facilidad
    plot_data['is_anomaly'] = plot_data['anomaly'] == -1
    return plot_data.to_dict(orient='records')