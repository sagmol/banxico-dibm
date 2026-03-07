"""
07_descarga_pdfs.py
-------------------
Descarga PDFs del subuniverso inflación (JEL E3x, E5x) del DIBM Banxico.
Guarda los PDFs en data/pdfs/inflacion/ y un log de descargas en data/processed/pdfs_log.csv.

Puede interrumpirse y reanudarse — omite archivos ya descargados.
"""

import requests
import pandas as pd
import time
import os
import sys
from pathlib import Path

# ── Rutas ─────────────────────────────────────────────────────────────────────
BASE = Path(__file__).parent.parent
PDF_DIR = BASE / "data" / "pdfs" / "inflacion"
LOG_FILE = BASE / "data" / "processed" / "pdfs_log.csv"
PDF_DIR.mkdir(parents=True, exist_ok=True)

# ── Cargar datos ───────────────────────────────────────────────────────────────
papers = pd.read_csv(BASE / "data/processed/papers.csv")
jel    = pd.read_csv(BASE / "data/processed/paper_jel.csv")

# Subuniverso inflación: E3x (precios) y E5x (política monetaria)
inf_claves = jel[jel["jel_code"].str.startswith(("E3", "E5"))]["clave_paper"].unique()
inf = papers[papers["clave"].isin(inf_claves) & papers["tiene_pdf_ing"]].copy()
inf = inf[inf["url_pdf_ing"].notna() & (inf["url_pdf_ing"] != "")]

print(f"Subuniverso inflación: {len(inf)} papers con PDF disponible")
print(f"Destino: {PDF_DIR}\n")

# ── Log de progreso ────────────────────────────────────────────────────────────
if LOG_FILE.exists():
    log = pd.read_csv(LOG_FILE)
    ya_descargados = set(log[log["status"] == "ok"]["clave"].tolist())
    print(f"Retomando — ya descargados: {len(ya_descargados)}")
else:
    log = pd.DataFrame(columns=["clave", "anio", "url", "archivo", "status", "bytes", "error"])
    ya_descargados = set()

# ── Headers para no ser bloqueado ─────────────────────────────────────────────
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/pdf,application/octet-stream,*/*",
    "Referer": "https://www.banxico.org.mx/",
}

# ── Descarga ───────────────────────────────────────────────────────────────────
resultados = []
total = len(inf)

for i, (_, row) in enumerate(inf.iterrows(), 1):
    clave = row["clave"]
    url   = row["url_pdf_ing"]
    anio  = row["anio"]
    nombre_archivo = f"{clave}.pdf"
    ruta_local = PDF_DIR / nombre_archivo

    sys.stdout.write(f"\r[{i:3d}/{total}] {clave}  ")
    sys.stdout.flush()

    # Saltar si ya fue descargado
    if clave in ya_descargados:
        print(f"[{i:3d}/{total}] {clave}  (ya descargado, omitiendo)")
        continue

    # Saltar si el archivo ya existe en disco
    if ruta_local.exists() and ruta_local.stat().st_size > 5000:
        print(f"[{i:3d}/{total}] {clave}  (archivo existe, omitiendo)")
        resultados.append({
            "clave": clave, "anio": anio, "url": url,
            "archivo": nombre_archivo, "status": "ok",
            "bytes": ruta_local.stat().st_size, "error": ""
        })
        continue

    try:
        resp = requests.get(url, headers=HEADERS, timeout=30, stream=True)
        resp.raise_for_status()

        content_type = resp.headers.get("Content-Type", "")
        if "pdf" not in content_type and "octet" not in content_type:
            raise ValueError(f"Content-Type inesperado: {content_type}")

        contenido = resp.content
        if len(contenido) < 5000:
            raise ValueError(f"Archivo demasiado pequeño ({len(contenido)} bytes)")

        ruta_local.write_bytes(contenido)

        print(f"[{i:3d}/{total}] {clave}  OK  ({len(contenido)/1024:.0f} KB)")
        resultados.append({
            "clave": clave, "anio": anio, "url": url,
            "archivo": nombre_archivo, "status": "ok",
            "bytes": len(contenido), "error": ""
        })

    except Exception as e:
        print(f"[{i:3d}/{total}] {clave}  ERROR: {e}")
        resultados.append({
            "clave": clave, "anio": anio, "url": url,
            "archivo": nombre_archivo, "status": "error",
            "bytes": 0, "error": str(e)
        })

    time.sleep(1.2)  # pausa cortés entre requests

# ── Guardar log ────────────────────────────────────────────────────────────────
nuevo_log = pd.DataFrame(resultados)
log_final = pd.concat([log, nuevo_log], ignore_index=True).drop_duplicates(subset=["clave"], keep="last")
log_final.to_csv(LOG_FILE, index=False)

# ── Resumen ────────────────────────────────────────────────────────────────────
ok     = log_final[log_final["status"] == "ok"]
errors = log_final[log_final["status"] == "error"]

print("\n" + "="*55)
print(f"  Descargados exitosamente : {len(ok)}")
print(f"  Errores                  : {len(errors)}")
if len(errors):
    print("\n  Claves con error:")
    for _, r in errors.iterrows():
        print(f"    {r['clave']} — {r['error']}")
print(f"\n  Log guardado en: {LOG_FILE}")
print(f"  PDFs en        : {PDF_DIR}")
print("="*55)
