"""
01_limpieza.py
==============
Transforma los JSON crudos del DIBM (documentos.json, autores.json) en tablas
relacionales limpias en CSV y una base SQLite.

Tablas generadas:
  papers          -> un registro por documento
  authors         -> un registro por autor único
  paper_authors   -> relación many-to-many, con orden de autoría
  jel_codes       -> catálogo de códigos JEL únicos
  paper_jel       -> relación many-to-many paper ↔ JEL
  paper_keywords  -> palabras clave por documento
  paper_topics    -> tema(s) asignado(s) por documento

Notas:
  - El JSON crudo tiene caracteres corruptos (mojibake) en los campos de texto
    en español. Se registra la situación pero NO se descarta ningún documento.
  - Los campos de texto en inglés están en buenas condiciones.
  - rutaArchivoIng / rutaResumenEsp son rutas de red internas de Banxico,
    no accesibles públicamente.
  - infoPublicacion.urlIng y urlResumenEsp son URLs públicas de banxico.org.mx.
"""

import json
import csv
import sqlite3
import os
import sys
import logging
from datetime import datetime
from pathlib import Path

# ── Rutas ──────────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).resolve().parent.parent
RAW_DIR    = BASE_DIR / "data" / "raw"
OUT_DIR    = BASE_DIR / "data" / "processed"
LOG_DIR    = BASE_DIR / "logs"

OUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ── Logging ────────────────────────────────────────────────────────────────────
log_path = LOG_DIR / f"01_limpieza_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_path, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


# ── Helpers ────────────────────────────────────────────────────────────────────
def load_json(path: Path) -> list | dict:
    """Carga un JSON; usa utf-8 con reemplazo para caracteres corruptos."""
    log.info(f"Cargando {path.name}...")
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        data = json.load(f)
    log.info(f"  → {len(data) if isinstance(data, list) else 'dict'} registros")
    return data


def clean_str(s):
    """Devuelve string limpio o None."""
    if s is None:
        return None
    s = str(s).strip()
    return s if s else None


def extract_year(clave: str) -> int | None:
    """Extrae el año de una clave tipo '2025-16'."""
    try:
        return int(clave.split("-")[0])
    except Exception:
        return None


def get_meta_values(metadatos: list, nombre: str) -> list[str]:
    """Extrae la lista de valores de un metadato por nombre."""
    for m in metadatos:
        if m.get("nombre") == nombre:
            valores = m.get("valoresMetadato", [])
            return [
                clean_str(
                    v.get("valorMetadatoCatalogo", {}).get("nombre")
                    or v.get("valorMetadatoCatalogo", {}).get("presentacionEsp")
                )
                for v in valores
                if v.get("valorMetadatoCatalogo")
            ]
    return []


def get_meta_single(metadatos: list, nombre: str) -> str | None:
    vals = get_meta_values(metadatos, nombre)
    return vals[0] if vals else None


# ── Carga de datos ─────────────────────────────────────────────────────────────
docs_raw    = load_json(RAW_DIR / "documentos.json")
autores_raw = load_json(RAW_DIR / "autores.json")

log.info(f"Documentos cargados: {len(docs_raw)}")
log.info(f"Autores cargados: {len(autores_raw)}")


# ══════════════════════════════════════════════════════════════════════════════
# 1. TABLA: papers
# ══════════════════════════════════════════════════════════════════════════════
log.info("Construyendo tabla 'papers'...")

papers = []
errors = []

for doc in docs_raw:
    try:
        clave  = clean_str(doc.get("clave"))
        anio   = extract_year(clave) if clave else None
        meta   = doc.get("metadatos", [])
        info   = doc.get("infoPublicacion") or {}

        # URLs públicas de PDF
        url_pdf_ing     = clean_str(info.get("urlIng"))
        url_resumen_esp = clean_str(info.get("urlResumenEsp"))
        fecha_pub       = clean_str(info.get("fechaPublicacion"))

        # Metadatos
        idiomas        = get_meta_values(meta, "Idioma")
        tema_principal = get_meta_single(meta, "Tema")

        papers.append({
            "id":               doc.get("id"),
            "clave":            clave,
            "anio":             anio,
            "decada":           (anio // 10 * 10) if anio else None,
            "titulo_esp":       clean_str(doc.get("tituloEsp")),
            "titulo_ing":       clean_str(doc.get("tituloIng")),
            "resumen_esp":      clean_str(doc.get("resumenEsp")),
            "resumen_ing":      clean_str(doc.get("resumenIng")),
            "status":           clean_str(doc.get("status")),
            "historico":        doc.get("historico"),
            "publicar":         doc.get("publicar"),
            "idiomas":          "|".join(i for i in idiomas if i),
            "tema":             tema_principal,
            "num_autores":      len(doc.get("autores", [])),
            "url_pdf_ing":      url_pdf_ing,
            "url_resumen_esp":  url_resumen_esp,
            "fecha_publicacion":fecha_pub,
            "fecha_creacion":   clean_str(doc.get("fechaCreacion")),
            "fecha_modificacion":clean_str(doc.get("fechaModificacion")),
            "tiene_pdf_ing":    bool(url_pdf_ing),
            "tiene_resumen_esp":bool(url_resumen_esp),
        })

    except Exception as e:
        errors.append({"clave": doc.get("clave"), "error": str(e), "etapa": "papers"})
        log.warning(f"Error en documento {doc.get('clave')}: {e}")

log.info(f"  → {len(papers)} papers, {len(errors)} errores")


# ══════════════════════════════════════════════════════════════════════════════
# 2. TABLAS: authors + paper_authors
# ══════════════════════════════════════════════════════════════════════════════
log.info("Construyendo tablas 'authors' y 'paper_authors'...")

authors_dict   = {}   # id_scai -> author record
paper_authors  = []

for doc in docs_raw:
    clave   = doc.get("clave")
    autores = doc.get("autores", [])

    for aut in autores:
        autor_id = aut.get("idScai") or aut.get("id")
        if not autor_id:
            continue

        # Registrar autor si es nuevo
        if autor_id not in authors_dict:
            nombre     = clean_str(aut.get("nombre"))
            primer_ap  = clean_str(aut.get("primerApellido"))
            segundo_ap = clean_str(aut.get("segundoApellido"))

            nombre_completo = " ".join(
                p for p in [nombre, primer_ap, segundo_ap] if p
            )

            authors_dict[autor_id] = {
                "id":              autor_id,
                "nombre":          nombre,
                "primer_apellido": primer_ap,
                "segundo_apellido":segundo_ap,
                "nombre_completo": nombre_completo,
                "presentacion":    clean_str(aut.get("presentacion")),
                "clave_usuario":   clean_str(aut.get("claveUsuario")),
                "status":          clean_str(aut.get("status")),
            }

        # Relación paper ↔ autor
        paper_authors.append({
            "clave_paper":  clave,
            "autor_id":     autor_id,
            "orden":        aut.get("orden"),
            "presentacion": clean_str(aut.get("presentacion")),
        })

authors = list(authors_dict.values())
log.info(f"  → {len(authors)} autores únicos, {len(paper_authors)} relaciones paper-autor")


# ══════════════════════════════════════════════════════════════════════════════
# 3. TABLAS: jel_codes + paper_jel + paper_keywords + paper_topics
# ══════════════════════════════════════════════════════════════════════════════
log.info("Construyendo tablas JEL, keywords y topics...")

jel_catalog  = {}   # codigo -> descripcion (si disponible)
paper_jel    = []
paper_kw     = []
paper_topics = []

for doc in docs_raw:
    clave = doc.get("clave")
    meta  = doc.get("metadatos", [])

    # JEL codes
    for m in meta:
        if m.get("nombre") == "JEL":
            for v in m.get("valoresMetadato", []):
                cat = v.get("valorMetadatoCatalogo", {})
                code = clean_str(cat.get("nombre"))
                desc = clean_str(
                    cat.get("presentacionEsp") or cat.get("presentacionIng")
                )
                if code:
                    if code not in jel_catalog:
                        jel_catalog[code] = desc
                    paper_jel.append({
                        "clave_paper": clave,
                        "jel_code":    code,
                    })

    # Palabras clave
    kws = get_meta_values(meta, "Palabras clave")
    for kw in kws:
        if kw:
            paper_kw.append({"clave_paper": clave, "keyword": kw})

    # Temas
    temas = get_meta_values(meta, "Tema")
    for t in temas:
        if t:
            paper_topics.append({"clave_paper": clave, "tema": t})

jel_codes = [{"codigo": k, "descripcion": v} for k, v in sorted(jel_catalog.items())]

log.info(f"  → {len(jel_codes)} códigos JEL únicos")
log.info(f"  → {len(paper_jel)} asignaciones paper-JEL")
log.info(f"  → {len(paper_kw)} palabras clave")
log.info(f"  → {len(paper_topics)} temas")


# ══════════════════════════════════════════════════════════════════════════════
# 4. GUARDAR CSVs
# ══════════════════════════════════════════════════════════════════════════════
def save_csv(records: list, filename: str):
    if not records:
        log.warning(f"Sin registros para {filename}")
        return
    path = OUT_DIR / filename
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)
    log.info(f"  ✓ {filename} ({len(records)} filas)")

log.info("Guardando CSVs...")
save_csv(papers,       "papers.csv")
save_csv(authors,      "authors.csv")
save_csv(paper_authors,"paper_authors.csv")
save_csv(jel_codes,    "jel_codes.csv")
save_csv(paper_jel,    "paper_jel.csv")
save_csv(paper_kw,     "paper_keywords.csv")
save_csv(paper_topics, "paper_topics.csv")

if errors:
    save_csv(errors, "errores_limpieza.csv")


# ══════════════════════════════════════════════════════════════════════════════
# 5. GUARDAR SQLite
# ══════════════════════════════════════════════════════════════════════════════
log.info("Construyendo base SQLite...")

db_path = OUT_DIR / "banxico_dibm.sqlite"
con = sqlite3.connect(db_path)
cur = con.cursor()

def create_and_insert(table: str, records: list):
    if not records:
        return
    cols   = list(records[0].keys())
    placeholders = ", ".join(["?"] * len(cols))
    col_defs = ", ".join(f'"{c}" TEXT' for c in cols)
    cur.execute(f'DROP TABLE IF EXISTS "{table}"')
    cur.execute(f'CREATE TABLE "{table}" ({col_defs})')
    rows = [tuple(str(r[c]) if r[c] is not None else None for c in cols) for r in records]
    cur.executemany(f'INSERT INTO "{table}" VALUES ({placeholders})', rows)
    log.info(f"  ✓ SQLite tabla '{table}' ({len(records)} filas)")

create_and_insert("papers",        papers)
create_and_insert("authors",       authors)
create_and_insert("paper_authors", paper_authors)
create_and_insert("jel_codes",     jel_codes)
create_and_insert("paper_jel",     paper_jel)
create_and_insert("paper_keywords",paper_kw)
create_and_insert("paper_topics",  paper_topics)

con.commit()
con.close()
log.info(f"  ✓ SQLite guardada en {db_path}")


# ══════════════════════════════════════════════════════════════════════════════
# 6. REPORTE DE COBERTURA
# ══════════════════════════════════════════════════════════════════════════════
total      = len(papers)
con_pdf    = sum(1 for p in papers if p["tiene_pdf_ing"])
con_res    = sum(1 for p in papers if p["tiene_resumen_esp"])
con_jel    = len({pj["clave_paper"] for pj in paper_jel})
con_tema   = len({pt["clave_paper"] for pt in paper_topics})
con_kw     = len({pk["clave_paper"] for pk in paper_kw})
con_abs_ing= sum(1 for p in papers if p["resumen_ing"])
con_abs_esp= sum(1 for p in papers if p["resumen_esp"])
anio_min   = min((p["anio"] for p in papers if p["anio"]), default=None)
anio_max   = max((p["anio"] for p in papers if p["anio"]), default=None)

reporte = f"""
══════════════════════════════════════════════
  REPORTE DE COBERTURA - DIBM Banxico
  {datetime.now().strftime('%Y-%m-%d %H:%M')}
══════════════════════════════════════════════
Total de documentos:          {total}
Rango temporal:               {anio_min} – {anio_max}
Autores únicos:               {len(authors)}
Códigos JEL únicos:           {len(jel_codes)}

Cobertura de campos:
  Con PDF inglés (URL):       {con_pdf:>4} / {total}  ({con_pdf/total*100:.1f}%)
  Con resumen ejecutivo ESP:  {con_res:>4} / {total}  ({con_res/total*100:.1f}%)
  Con código(s) JEL:          {con_jel:>4} / {total}  ({con_jel/total*100:.1f}%)
  Con tema asignado:          {con_tema:>4} / {total}  ({con_tema/total*100:.1f}%)
  Con palabras clave:         {con_kw:>4} / {total}  ({con_kw/total*100:.1f}%)
  Con resumen en inglés:      {con_abs_ing:>4} / {total}  ({con_abs_ing/total*100:.1f}%)
  Con resumen en español:     {con_abs_esp:>4} / {total}  ({con_abs_esp/total*100:.1f}%)

Errores en limpieza:          {len(errors)}
══════════════════════════════════════════════
"""

print(reporte)
log.info(reporte)

with open(LOG_DIR / "reporte_cobertura.txt", "w", encoding="utf-8") as f:
    f.write(reporte)

log.info("Script completado.")
