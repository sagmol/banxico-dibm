"""
10h_proxy_papers.py
Busca papers del corpus que usan los proxies ortodoxos para cada debate.
Agrega campo proxy_papers a debates_papers.json.
"""

import pandas as pd
import json
import re

PAPERS_CSV  = "C:/Users/USER/OneDrive/Escritorio/claudio/banxico-dibm/data/processed/papers.csv"
AUTHORS_CSV = "C:/Users/USER/OneDrive/Escritorio/claudio/banxico-dibm/data/processed/paper_authors.csv"
JSON_IN     = "C:/Users/USER/OneDrive/Escritorio/claudio/banxico-dibm/docs/data/debates_papers.json"
JSON_OUT    = JSON_IN   # overwrite in place

# ── 1. Cargar datos ─────────────────────────────────────────────────────────
papers  = pd.read_csv(PAPERS_CSV,  encoding="utf-8-sig", on_bad_lines="skip")
authors = pd.read_csv(AUTHORS_CSV, encoding="utf-8-sig", on_bad_lines="skip")

# Agrupar autores por clave de paper (en orden)
def get_autores(clave):
    rows = authors[authors["clave_paper"] == clave].sort_values("orden")
    return rows["presentacion"].tolist()

# ── 2. Función de búsqueda ───────────────────────────────────────────────────
def search_papers(terms, max_results=20, snippet_len=120):
    """
    terms: list of strings (case-insensitive OR search)
    Returns list of dicts: {clave, anio, titulo, autores, snippet, url}
    """
    pattern = re.compile("|".join(re.escape(t) for t in terms), re.IGNORECASE)

    results = []
    seen = set()
    for _, row in papers.sort_values("anio").iterrows():
        clave = str(row.get("clave", ""))
        if clave in seen:
            continue

        # Textos a buscar
        texts = {
            "resumen_ing": str(row.get("resumen_ing", "") or ""),
            "resumen_esp": str(row.get("resumen_esp", "") or ""),
            "titulo_ing":  str(row.get("titulo_ing",  "") or ""),
        }

        matched_snippet = None
        for field, text in texts.items():
            m = pattern.search(text)
            if m:
                start = max(0, m.start() - 60)
                end   = min(len(text), m.end() + 60)
                raw   = text[start:end]
                # Wrap matched term with <mark>
                snippet = ("…" if start > 0 else "") + \
                          pattern.sub(lambda x: f"<mark>{x.group()}</mark>", raw) + \
                          ("…" if end < len(text) else "")
                matched_snippet = snippet
                break

        if not matched_snippet:
            continue

        seen.add(clave)
        titulo = str(row.get("titulo_ing") or row.get("titulo_esp") or "")
        url    = str(row.get("url_pdf_ing", "") or "")
        if url == "nan":
            url = None

        results.append({
            "clave":   clave,
            "anio":    int(row.get("anio", 0)),
            "titulo":  titulo.strip(),
            "autores": get_autores(clave),
            "snippet": matched_snippet.strip(),
            "url":     url or None,
        })

        if len(results) >= max_results:
            break

    return results

# ── 3. Definir búsquedas por debate ─────────────────────────────────────────
SEARCHES = {
    "instab_fin": [
        "financial friction", "financial accelerator",
        "credit channel", "credit spread", "balance sheet channel",
        "financial conditions", "systemic risk", "bank lending channel",
    ],
    "dem_efectiva": [
        "output gap", "demand management", "aggregate demand",
        "demand shock", "cyclical component",
    ],
    "dinero_endog": [
        "Taylor rule", "monetary policy rule", "interest rate rule",
        "feedback rule", "instrument rule",
    ],
    "conflict_infl": [
        "Phillips curve", "wage-price spiral", "wage setting",
        "markup", "price setting", "inflation expectations",
    ],
    "sraffa": [
        "term structure", "yield curve", "term premium",
        "yield spread", "term structure of interest",
    ],
    "thirlwall": [
        "balance of payments", "current account deficit",
        "currency crisis", "exchange rate crisis", "sudden stop",
        "capital account", "external constraint",
    ],
    "salario_min": [
        "minimum wage", "salario m", "wage floor",
        "labor market", "minimum salary",
    ],
}

# ── 4. Cargar JSON y agregar proxy_papers ────────────────────────────────────
with open(JSON_IN, encoding="utf-8") as f:
    data = json.load(f)

for key, terms in SEARCHES.items():
    results = search_papers(terms)
    if key not in data:
        data[key] = {"label": key, "n": 0, "papers": []}
    data[key]["proxy_papers"] = results
    print(f"{key}: {len(results)} proxy papers encontrados")

# ── 5. Guardar ───────────────────────────────────────────────────────────────
with open(JSON_OUT, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"\nGuardado: {JSON_OUT}")
