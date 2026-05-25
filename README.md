# OpsGuard AIOps · Detección automática de anomalías

Proyecto académico orientado a producción para detectar anomalías en métricas IoT mediante AIOps, Machine Learning no supervisado y persistencia local en base de datos.

## Caso de uso

**Detección automática de anomalías.** La solución analiza métricas, eventos y señales operativas de dispositivos inteligentes para identificar comportamientos inusuales antes de que se conviertan en fallas o incidentes de seguridad.

## Funcionalidades implementadas

- Carga de archivos CSV desde una interfaz web.
- Validación de columnas mínimas requeridas.
- Detección automática de anomalías con Isolation Forest.
- Uso de variables operativas y de seguridad: CPU, memoria, tráfico de red, paquetes, latencia, intentos fallidos, cifrado y variación geográfica.
- Dashboard estilo NOC/SOC con KPIs, gráficas, tabla de anomalías y puntaje de riesgo.
- Persistencia local con SQLite sin servicios pagos.
- Historial de análisis guardado en base de datos.
- Generación de alertas operativas por severidad.
- API REST documentada automáticamente en `/docs`.
- Endpoint de salud `/health`.
- Simulación gratuita de tiempo real sobre datos persistidos.

## Arquitectura

```text
CSV / Métricas IoT
        ↓
Frontend web
        ↓
FastAPI /upload
        ↓
Validación + Pandas
        ↓
StandardScaler + Isolation Forest
        ↓
SQLite
  ├─ analysis_runs
  ├─ observations
  └─ alerts
        ↓
Dashboard NOC/SOC + API REST
```

## Base de datos

Se usa SQLite porque permite persistencia local sin servidor, cuentas ni pagos. La base se crea automáticamente en:

```text
data/aiops_observability.db
```

Tablas principales:

| Tabla | Propósito |
|---|---|
| `analysis_runs` | Guarda cada ejecución del análisis: archivo, fecha, modelo, sensibilidad, registros y anomalías. |
| `observations` | Guarda cada evento del CSV con métricas, etiqueta real si existe, predicción ML y puntaje de riesgo. |
| `alerts` | Guarda alertas generadas a partir de anomalías con severidad y descripción operacional. |

## Requisitos

- Python 3.11 recomendado.
- Navegador web moderno.

## Instalación y ejecución

```bash
python -m venv venv
```

Windows:

```bash
venv\Scripts\activate
```

Mac/Linux:

```bash
source venv/bin/activate
```

Instalar dependencias:

```bash
pip install -r requirements.txt
```

Ejecutar:

```bash
uvicorn main:app --reload
```

Abrir:

```text
http://127.0.0.1:8000
```

Documentación API:

```text
http://127.0.0.1:8000/docs
```

## Endpoints principales

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/` | Dashboard web. |
| `GET` | `/health` | Estado de la API y base de datos. |
| `POST` | `/upload?contamination=0.05` | Sube CSV, detecta anomalías, guarda análisis y genera alertas. |
| `GET` | `/analyses` | Lista análisis guardados. |
| `GET` | `/analyses/{run_id}` | Consulta un análisis completo. |
| `GET` | `/alerts` | Lista alertas generadas. |
| `DELETE` | `/analyses` | Borra la base local de análisis. |
| `GET` | `/realtime/simulated?run_id=1&start=0&limit=25` | Simula lectura por lotes tipo tiempo real. |

## Dataset esperado

Columnas mínimas obligatorias:

```text
timestamp, cpu_usage, network_in_kb, packet_rate
```

Columnas adicionales recomendadas:

```text
device_id, device_type, memory_usage, network_out_kb,
avg_response_time_ms, service_access_count, failed_auth_attempts,
is_encrypted, geo_location_variation, label
```

## Modelo ML

El proyecto usa `IsolationForest`, un algoritmo de detección de anomalías no supervisado. La sensibilidad se controla desde la interfaz mediante el parámetro `contamination`.

Ejemplo:

- `0.05` equivale a esperar aproximadamente 5% de anomalías.
- `0.10` equivale a una detección más sensible, aproximadamente 10%.

## Escenario académico gratis

- Backend local con FastAPI.
- Base local SQLite.
- Dataset público/sintético.
- Frontend HTML/CSS/JS.
- Sin servicios cloud pagos.

## Escenario producción propuesto

La versión actual se puede defender como prototipo orientado a producción. Para una organización real se recomienda:

- Migrar SQLite a PostgreSQL o TimescaleDB.
- Cambiar carga CSV por ingesta continua mediante API, cola o streaming.
- Agregar autenticación y roles.
- Integrar alertas con correo, Slack, Teams o webhook.
- Agregar pruebas automatizadas y migraciones de base de datos.
- Contenerizar con Docker.
- Agregar monitoreo de la propia API.

## Equipo

Grupo A: Juan José Rodríguez, Juan Daniel González, Fabián Sneyder Moya.
