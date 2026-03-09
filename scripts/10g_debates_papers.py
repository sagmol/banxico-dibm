"""
10g_debates_papers.py
----------------------
Para cada debate "ausente o marginal", identifica qué papers lo mencionan
en sus abstracts y extrae el detalle (título, año, autores, snippet, URL PDF).

Output: docs/data/debates_papers.json
"""
import json, sys, re, pandas as pd
from pathlib import Path
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8")

BASE         = Path(__file__).parent.parent
papers       = pd.read_csv(BASE / "data/processed/papers.csv")
pa           = pd.read_csv(BASE / "data/processed/paper_authors.csv")

# Mapa autor_id → nombre
autores_map = pa.groupby("clave_paper")["presentacion"].apply(list).to_dict()

papers["texto"] = (
    papers["resumen_ing"].fillna("") + " " + papers["resumen_esp"].fillna("")
).str.strip()
papers["texto_l"] = papers["texto"].str.lower()
papers = papers[papers["texto_l"].str.len() > 50].copy()

# ── Mismos debates que en temporal_evolucion.html ────────────────────────────
DEBATES = [
    # key, label, términos de búsqueda
    ("minsky",       "Minsky / Hipótesis de Inestabilidad Financiera",
     ["minsky", "financial instability hypothesis", "hipótesis de inestabilidad"]),
    ("kalecki",      "Kalecki / Demanda efectiva",
     ["kalecki", "effective demand", "demanda efectiva"]),
    ("dinero_endog", "Dinero endógeno (Kaldor, Moore, Lavoie)",
     ["endogenous money", "horizontalism", "endogenous credit", "dinero endógeno",
      "monetary circuit", "circuit theory", "loans create deposit", "lavoie", "wray"]),
    ("postkeyn",     "Post-keynesian (como framework)",
     ["post-keynesian", "post keynesian"]),
    ("sfc",          "Stock-flow consistent / Godley / balances sect.",
     ["stock-flow", "godley", "sectoral balances"]),
    ("thirlwall",    "Thirlwall / restricción externa (BOP)",
     ["thirlwall", "balance of payments constrain", "bop-constrain",
      "restricción externa", "external constraint"]),
    ("prebisch",     "Centro-periferia / Heterogeneidad estructural (CEPAL)",
     ["prebisch", "cepal", "eclac", "prebisch-singer",
      "dependency theory", "deterioro de los términos",
      "centro-periferia", "heterogeneidad estructural latinoam",
      "structuralist latin", "furtado", "sunkel"]),
    ("infl_struct",  "Inflación estructural / conflicto distributivo",
     ["structuralist", "conflict inflation", "cost-push inflation",
      "inflación estructural", "keynesiano-estructuralista"]),
    ("multiplicador","Multiplicador fiscal / crowding-in",
     ["fiscal multiplier", "crowding in", "crowd in",
      "fiscal stimulus", "multiplicador fiscal"]),
    ("estanc",       "Estancamiento secular (Summers)",
     ["secular stagnation", "estancamiento secular"]),
    ("desigualdad",  "Desigualdad / distribución del ingreso (Piketty)",
     ["piketty", "inequality", "desigualdad"]),
    ("genero",       "Perspectiva de género en macroeconomía",
     ["gender gap", "gender wage", "brecha salarial",
      "perspectiva de género", "feminist econ"]),
    ("financializ",  "Financialización",
     ["financiali", "financiación del capital"]),
]

def snippet(texto, terminos, ventana=80):
    """Extrae contexto alrededor del primer término encontrado."""
    tl = texto.lower()
    for term in terminos:
        idx = tl.find(term)
        if idx >= 0:
            start = max(0, idx - ventana)
            end   = min(len(texto), idx + len(term) + ventana)
            s = texto[start:end].strip()
            # Resaltar término (para HTML)
            pat = re.compile(re.escape(term), re.IGNORECASE)
            s = pat.sub(f"<mark>{term}</mark>", s, count=1)
            return ("…" if start > 0 else "") + s + ("…" if end < len(texto) else "")
    return ""

resultado = {}
for key, label, terminos in DEBATES:
    mask = papers["texto_l"].apply(lambda t: any(term in t for term in terminos))
    sub  = papers[mask].copy()
    papers_list = []
    for _, row in sub.iterrows():
        autores = autores_map.get(row["clave"], [])
        titulo  = row["titulo_ing"] if pd.notna(row["titulo_ing"]) and str(row["titulo_ing"]).strip() else row["titulo_esp"]
        url     = row["url_pdf_ing"] if pd.notna(row["url_pdf_ing"]) else None
        papers_list.append({
            "clave":   row["clave"],
            "anio":    int(row["anio"]),
            "titulo":  str(titulo).strip(),
            "autores": autores[:4],  # máximo 4
            "snippet": snippet(row["texto"], terminos),
            "url":     url,
        })
    papers_list.sort(key=lambda x: x["anio"])
    resultado[key] = {
        "label":  label,
        "n":      len(papers_list),
        "papers": papers_list,
    }

outpath = BASE / "docs/data/debates_papers.json"
json.dump(resultado, open(outpath, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"✓ {outpath}")
print()
for key, v in resultado.items():
    if v["n"] > 0:
        print(f"\n{v['label']} ({v['n']} papers):")
        for p in v["papers"]:
            print(f"  [{p['anio']}] {p['clave']} — {p['titulo'][:70]}")
            print(f"    Autores: {', '.join(p['autores'][:3])}")
