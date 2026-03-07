# Corpus Intelectual del Banco de México (DIBM)

Análisis bibliométrico, temático e histórico de los documentos de investigación del Banco de México (1978–2025).

## Propósito

Este proyecto construye una base de datos estructurada del corpus completo de documentos de investigación del DIBM (Documentos de Investigación del Banco de México) y los analiza para responder preguntas como:

- ¿Quiénes escriben? ¿Cómo evolucionan las redes de coautoría?
- ¿Qué temas predominan y cómo cambian con el tiempo?
- ¿Qué métodos se usan con mayor frecuencia?
- ¿Qué papel juega el cambio de régimen hacia metas de inflación en la agenda de investigación?
- ¿Con quiénes dialogan intelectualmente los investigadores del Banco?

## Datos

**Fuente:** API pública del DIBM — `https://www.banxico.org.mx/DIBM/web/`

| Archivo | Descripción |
|---|---|
| `data/raw/documentos.json` | 563 documentos con títulos, resúmenes, metadatos y autores |
| `data/raw/autores.json` | 447 autores con su producción asociada |
| `data/processed/papers.csv` | Tabla principal de documentos (1 fila por paper) |
| `data/processed/authors.csv` | Autores únicos |
| `data/processed/paper_authors.csv` | Relación paper ↔ autor con orden de autoría |
| `data/processed/jel_codes.csv` | Catálogo de 379 códigos JEL únicos |
| `data/processed/paper_jel.csv` | Asignaciones paper ↔ JEL (1499 relaciones) |
| `data/processed/paper_topics.csv` | Temas por documento |
| `data/processed/banxico_dibm.sqlite` | Base SQLite con todas las tablas anteriores |

## Cobertura del corpus

| Variable | Cobertura |
|---|---|
| Total documentos | 563 |
| Rango temporal | 1978 – 2025 |
| Autores únicos | 447 |
| Códigos JEL únicos | 379 |
| Con URL de PDF (inglés) | 63.8% |
| Con código(s) JEL | 75.1% |
| Con tema asignado | 97.7% |
| Con resumen en inglés | 75.7% |
| Con resumen en español | 100% |

## Estructura del repositorio

```
banxico-dibm/
├── data/
│   ├── raw/            JSON originales del API de Banxico
│   └── processed/      CSVs limpios + SQLite
├── notebooks/          Análisis en Jupyter
├── scripts/            Scripts Python de procesamiento
├── docs/               Sitio web (GitHub Pages)
│   └── charts/         Visualizaciones interactivas (Plotly HTML)
├── logs/               Logs de ejecución y reportes de cobertura
└── README.md
```

## Instalación

Se requiere Python 3.10+ (Anaconda recomendado).

```bash
# Dependencias principales (ya incluidas en Anaconda)
pandas
networkx
plotly
sqlite3  # stdlib
```

## Orden de ejecución

```bash
# 1. Re-fetchear datos frescos del API de Banxico (opcional si ya existen)
python scripts/00_fetch.py

# 2. Limpiar y construir tablas relacionales
python scripts/01_limpieza.py

# 3. Análisis temporal
jupyter notebook notebooks/02_temporal.ipynb

# 4. Red de coautoría
jupyter notebook notebooks/03_autores_redes.ipynb

# 5. Análisis JEL y temas
jupyter notebook notebooks/04_jel_temas.ipynb

# 6. Análisis de abstracts (clusters temáticos)
jupyter notebook notebooks/05_texto_abstracts.ipynb
```

## Etapas del proyecto

### Etapa 1 — Base de datos (completada)
Extracción, limpieza y estructuración de los 563 documentos en tablas relacionales.

### Etapa 2 — Análisis del corpus (en curso)
- Distribución temporal de la producción
- Evolución de temas (JEL codes) por período histórico
- Redes de coautoría
- Clusters temáticos por similitud de abstracts

### Etapa 3 — Red de citas (planeada)
Descarga de PDFs del subuniverso de documentos sobre inflación y política monetaria, extracción de bibliografías y construcción de la red intelectual.

## Períodos históricos de análisis

El análisis distingue al menos tres etapas:
1. **Pre-estabilización (1978–1994):** producción escasa y dispersa
2. **Transición (1995–2001):** consolidación del DIBM, ajuste post-crisis
3. **Régimen de metas de inflación (2002–presente):** producción sistemática, JEL codes disponibles

## Limitaciones conocidas

- Los documentos anteriores a 1995 tienen cobertura escasa (menos del 10% del corpus).
- Las "Palabras clave" no están disponibles en el API actual (campo vacío).
- El 36% de los documentos no tiene URL de PDF disponible públicamente.
- El análisis de bibliografías requiere descarga y parseo de PDFs (Etapa 3).

## Fuente

Banco de México — Documentos de Investigación (DIBM)
https://www.banxico.org.mx/DIBM/
