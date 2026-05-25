# Entregable AIOps · Detección automática de anomalías

## 1. Información general

**Equipo:** Grupo A  
**Integrantes:** Juan José Rodríguez, Juan Daniel González, Fabián Sneyder Moya  
**Caso de uso:** Detección automática de anomalías  
**Dataset:** Anomaly Detection and Threat Intelligence Dataset  
**Producto:** OpsGuard AIOps Control Center

## 2. Resumen ejecutivo

OpsGuard AIOps es una solución de observabilidad inteligente para sistemas IoT que permite cargar métricas operativas desde archivos CSV, analizar patrones mediante Machine Learning no supervisado, detectar anomalías y generar alertas operativas. La solución fue mejorada para acercarse a un escenario productivo sin requerir servicios pagos: incluye API REST, base de datos SQLite, dashboard tipo NOC/SOC, historial persistente de análisis, alertamiento y documentación automática de endpoints.

El sistema permite apoyar a equipos de operaciones TI en la identificación temprana de comportamientos inusuales relacionados con uso de CPU, memoria, tráfico de red, tasa de paquetes, tiempos de respuesta, intentos fallidos de autenticación y variaciones geográficas.

## 3. Problema

Los sistemas inteligentes e IoT generan grandes volúmenes de datos operativos. Revisar manualmente estas métricas puede retrasar la detección de fallos, ataques o degradación del servicio. El problema principal es reducir el tiempo de identificación de comportamientos anómalos y convertir datos técnicos en alertas comprensibles para equipos de TI.

## 4. Objetivo general

Diseñar e implementar una solución basada en AIOps para detectar automáticamente anomalías en métricas y eventos de dispositivos IoT, permitiendo visualizar resultados, generar alertas y almacenar el historial de análisis en una base de datos local.

## 5. Objetivos específicos

- Cargar y procesar archivos CSV con métricas operativas.
- Aplicar un modelo de detección de anomalías no supervisado.
- Visualizar métricas y anomalías en un dashboard web.
- Generar alertas con severidad operacional.
- Persistir análisis, observaciones y alertas en una base de datos.
- Diseñar una arquitectura escalable hacia producción.

## 6. Alcance funcional

| Funcionalidad | Estado |
|---|---|
| Carga de CSV | Implementado |
| Validación de datos mínimos | Implementado |
| Detección de anomalías con Isolation Forest | Implementado |
| Dashboard con KPIs y gráficas | Implementado |
| Identificación visual de anomalías | Implementado |
| Historial persistente | Implementado con SQLite |
| Alertas operativas | Implementado |
| API REST documentada | Implementado con FastAPI `/docs` |
| Simulación de tiempo real | Implementado como endpoint simulado sobre datos persistidos |
| Tiempo real real con streaming | Propuesto para evolución |

## 7. Arquitectura de solución

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

### 7.1 Capa de datos

La solución usa SQLite como base de datos local sin costo. Esta base permite guardar:

- Ejecuciones de análisis.
- Registros originales enriquecidos con predicción ML.
- Alertas generadas.

### 7.2 Capa analítica

El modelo utiliza Isolation Forest sobre variables numéricas del dataset. Se normalizan las métricas con StandardScaler y se genera una predicción de anomalía junto con un puntaje de riesgo relativo.

### 7.3 Capa de visualización

El frontend presenta un tablero tipo NOC/SOC con:

- KPIs principales.
- Gráficos de recursos, red, tráfico y riesgo.
- Tabla de anomalías.
- Historial de análisis.
- Panel de alertas.
- Vista de arquitectura.

## 8. Modelo de base de datos

| Tabla | Propósito |
|---|---|
| `analysis_runs` | Guarda metadatos de cada análisis: archivo, fecha, modelo, sensibilidad, número de registros y anomalías. |
| `observations` | Guarda cada evento del CSV con métricas, etiqueta real si existe, predicción y puntaje de riesgo. |
| `alerts` | Guarda alertas generadas desde anomalías con severidad, descripción y métrica asociada. |

## 9. Variables analizadas

| Variable | Uso |
|---|---|
| `cpu_usage` | Detectar sobrecarga de procesamiento. |
| `memory_usage` | Detectar presión de memoria. |
| `network_in_kb` | Detectar tráfico entrante anormal. |
| `network_out_kb` | Detectar tráfico saliente anormal. |
| `packet_rate` | Detectar variaciones en volumen de paquetes. |
| `avg_response_time_ms` | Detectar degradación del servicio. |
| `service_access_count` | Detectar cambios en uso de servicios. |
| `failed_auth_attempts` | Detectar señales de ataques o accesos fallidos. |
| `is_encrypted` | Señal de postura de seguridad. |
| `geo_location_variation` | Detectar comportamiento geográfico inusual. |

## 10. Cronograma

| Fase | Actividad | Duración estimada | Entregable |
|---|---|---:|---|
| 1 | Análisis del caso de uso y dataset | 2 días | Alcance y variables |
| 2 | Implementación backend FastAPI | 3 días | API funcional |
| 3 | Implementación modelo ML | 2 días | Detección de anomalías |
| 4 | Implementación base de datos SQLite | 2 días | Persistencia local |
| 5 | Diseño dashboard NOC/SOC | 3 días | Interfaz formal |
| 6 | Alertas e historial | 2 días | Panel operacional |
| 7 | Pruebas y documentación | 2 días | README y entregable |
| 8 | Preparación de sustentación | 1 día | Guion de exposición |

## 11. Modelo financiero

### 11.1 Escenario académico sin costo desembolsado

| Concepto | Costo directo | Costo indirecto | Comentario |
|---|---:|---:|---|
| Dataset público/sintético | $0 COP | $0 COP | Fuente académica abierta |
| FastAPI, Pandas, scikit-learn | $0 COP | $0 COP | Software libre |
| SQLite | $0 COP | $0 COP | Base de datos local |
| Frontend HTML/CSS/JS | $0 COP | $0 COP | Sin licencias |
| Infraestructura local | $0 COP | $0 COP | Computadores del equipo |
| Mano de obra académica | $0 COP | $1.800.000 COP valorizados | 3 estudiantes x 40 h x $15.000 COP/h |
| Energía e internet | $0 COP | $50.000 COP estimados | Uso académico |
| **Total desembolsado** | **$0 COP** | **$1.850.000 COP valorizados** | Prototipo académico |

### 11.2 Escenario producción sin servicios pagos iniciales

Este escenario busca acercarse a producción sin pagar servicios externos, ejecutando la aplicación en una máquina institucional, computador servidor o VM local.

| Concepto | Costo directo mensual | Comentario |
|---|---:|---|
| Servidor local/institucional | $0 COP adicional | Se usa infraestructura existente |
| SQLite | $0 COP | Suficiente para prototipo y baja concurrencia |
| Software base | $0 COP | Python y librerías open source |
| Dominio público | $0 COP | No incluido; acceso por IP/red interna |
| Soporte operativo | $800.000 COP valorizados | Dedicación parcial de responsable TI |
| Mantenimiento evolutivo | $600.000 COP valorizados | Mejoras, pruebas, documentación |
| **Total desembolsado** | **$0 COP** | No hay pagos cloud |
| **Total valorizado mensual** | **$1.400.000 COP** | Mano de obra estimada |

### 11.3 Beneficio esperado

La solución reduce el esfuerzo manual de revisión de métricas y permite priorizar eventos anómalos. El beneficio se puede expresar como reducción del tiempo medio de detección de incidentes, mejor visibilidad operacional y generación de alertas más accionables.

## 12. Escenario de evolución a producción real

Para un ambiente empresarial se recomienda:

- Reemplazar SQLite por PostgreSQL o TimescaleDB.
- Usar contenedores Docker.
- Implementar autenticación y roles.
- Agregar integraciones con correo, Slack, Teams o webhooks.
- Consumir métricas en tiempo real desde APIs, agentes, colas o streaming.
- Implementar pruebas automatizadas.
- Agregar migraciones de base de datos.
- Monitorear la propia API.

## 13. Guion corto de sustentación

Nuestro proyecto se llama OpsGuard AIOps y está orientado a la detección automática de anomalías en sistemas IoT. La solución permite cargar archivos CSV con métricas operativas y de seguridad, procesarlos con FastAPI y analizarlos mediante un modelo Isolation Forest. A diferencia de una entrega básica, esta versión incorpora persistencia en SQLite, historial de análisis, generación de alertas, dashboard tipo NOC/SOC y documentación de API.

El modelo identifica registros cuyo comportamiento se aleja de la línea base normal. Cada análisis queda guardado en base de datos junto con sus observaciones y alertas, lo cual permite consultar resultados posteriormente. La solución actual funciona sin costos de infraestructura externa y está diseñada para evolucionar a producción mediante PostgreSQL, ingesta en tiempo real, autenticación e integración con canales de alerta.

## 14. Conclusión

OpsGuard AIOps cumple el objetivo de diseñar e implementar una solución funcional para detección automática de anomalías. La versión final no se limita a una carga de CSV y gráficos, sino que incorpora elementos propios de una solución TI más formal: API, persistencia, historial, alertamiento, modelo analítico y diseño de arquitectura escalable.
