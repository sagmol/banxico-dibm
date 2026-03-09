"""
10f_author_dsge.py
-------------------
¿Quién lleva el toolkit NK-DSGE al Banxico?
Fingerprint por autor: cruce de vocabulario NK-DSGE en abstracts con autoría.

Output: docs/data/author_dsge.json
"""
import json, sys, ast, pandas as pd
from pathlib import Path
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8")

BASE         = Path(__file__).parent.parent
papers       = pd.read_csv(BASE / "data/processed/papers.csv")[["clave","anio","decada"]]
paper_authors= pd.read_csv(BASE / "data/processed/paper_authors.csv")
nlp          = pd.read_csv(BASE / "data/processed/papers_nlp.csv")

# Cargar conceptos del script 10d para reutilizar
CONCEPTOS = {
    "dsge":               ["dsge", "dynamic stochastic general equilibrium", "dynamic stochastic"],
    "inflation_exp":      ["inflation expectations", "inflation expectation", "expectativas de inflación",
                           "expectativas inflacionarias", "inflationary expectations", "inflation anchoring"],
    "taylor_rule":        ["taylor rule", "taylor principle", "taylor-type rule",
                           "taylor reaction", "regla de taylor", "interest rate rule"],
    "calvo":              ["calvo", "staggered prices", "staggered price", "price stickiness",
                           "sticky prices", "sticky price", "nominal rigidities",
                           "nominal rigidity", "price rigidity"],
    "new_keynesian":      ["new keynesian", "new-keynesian", "nk model",
                           "nkpc", "new keynesian phillips", "new-keynesian phillips"],
    "output_gap":         ["output gap", "output-gap", "brecha del producto",
                           "brecha de producto", "production gap"],
    "financial_frictions":["financial frictions", "financial friction", "credit frictions",
                           "financial accelerator", "credit conditions", "credit market frictions",
                           "credit constraints", "collateral constraint"],
    "rational_exp":       ["rational expectations", "rational expectation",
                           "expectativas racionales", "model-consistent expectations",
                           "model consistent expectations"],
    "phillips_curve":     ["phillips curve", "phillips-curve", "curva de phillips", "phillips relation"],
    "bayesian":           ["bayesian", "bayesian estimation", "bayesian inference",
                           "bayes factor", "posterior distribution", "prior distribution"],
    "inflation_targeting":["inflation targeting", "inflation target", "inflation-targeting",
                           "meta de inflación", "objetivo de inflación", "inflation target framework",
                           "it framework", "price stability mandate"],
}

LABELS = {
    "dsge":"DSGE", "inflation_exp":"Inflation expectations",
    "taylor_rule":"Taylor rule", "calvo":"Calvo/sticky",
    "new_keynesian":"New Keynesian", "output_gap":"Output gap",
    "financial_frictions":"Fin. frictions", "rational_exp":"Rational exp.",
    "phillips_curve":"Phillips curve", "bayesian":"Bayesian",
    "inflation_targeting":"Inflation targeting",
}

# ── Re-detección de conceptos por paper (nivel granular) ─────────────────────
papers_full = pd.read_csv(BASE / "data/processed/papers.csv")
papers_full["texto"] = (
    papers_full["resumen_ing"].fillna("") + " " + papers_full["resumen_esp"].fillna("")
).str.strip().str.lower()
papers_full = papers_full[papers_full["texto"].str.len() > 50]

def detectar(texto):
    result = {}
    for key, terms in CONCEPTOS.items():
        result[key] = any(t in texto for t in terms)
    return result

papers_full["conceptos"] = papers_full["texto"].apply(detectar)
papers_full["n_conceptos"] = papers_full["conceptos"].apply(lambda d: sum(d.values()))
papers_full["tiene_nk"] = papers_full["n_conceptos"] > 0

# ── Merge con autores ─────────────────────────────────────────────────────────
merged = paper_authors.merge(
    papers_full[["clave","anio","decada","n_conceptos","tiene_nk","conceptos"]],
    left_on="clave_paper", right_on="clave", how="inner"
)

# ── Estadísticas por autor ────────────────────────────────────────────────────
autor_stats = []
for autor_id, grp in merged.groupby("autor_id"):
    nombre = grp["presentacion"].mode()[0] if len(grp) > 0 else str(autor_id)
    total = len(grp)
    if total < 2:
        continue  # solo autores con >= 2 papers

    nk_papers = grp[grp["tiene_nk"]]
    n_nk = len(nk_papers)
    pct_nk = round(n_nk / total * 100, 1)
    nk_score = int(grp["n_conceptos"].sum())  # intensidad total

    # Primer año NK
    primer_nk = int(nk_papers["anio"].min()) if len(nk_papers) > 0 else None

    # Qué conceptos usa (suma por concepto)
    conceptos_count = defaultdict(int)
    for _, row in grp.iterrows():
        for k, v in row["conceptos"].items():
            if v:
                conceptos_count[k] += 1
    top_conceptos = sorted(conceptos_count.items(), key=lambda x: -x[1])[:5]

    # Evolución por año
    evol = []
    for anio, sg in grp.groupby("anio"):
        evol.append({
            "anio": int(anio),
            "n_papers": len(sg),
            "n_nk": int(sg["tiene_nk"].sum()),
        })

    autor_stats.append({
        "autor_id":     int(autor_id),
        "nombre":       nombre,
        "total_papers": total,
        "n_nk":         n_nk,
        "pct_nk":       pct_nk,
        "nk_score":     nk_score,
        "primer_nk":    primer_nk,
        "top_conceptos": [{"key": k, "label": LABELS[k], "n": v} for k, v in top_conceptos],
        "evolucion":    evol,
    })

# Ordenar por nk_score descendente
autor_stats.sort(key=lambda x: (-x["nk_score"], -x["n_nk"]))

# ── Top autores NK (para la visualización principal) ─────────────────────────
top_nk = [a for a in autor_stats if a["n_nk"] > 0][:20]

# ── Distribución global ───────────────────────────────────────────────────────
total_autores = len(autor_stats)
autores_con_nk = len([a for a in autor_stats if a["n_nk"] > 0])
autores_dsge = len([a for a in autor_stats
                    if any(c["key"]=="dsge" for c in a["top_conceptos"])])

# ── Concentración: top 5 autores NK concentran qué % del total NK? ───────────
total_nk_papers = sum(a["n_nk"] for a in autor_stats)
top5_nk = sum(a["n_nk"] for a in top_nk[:5])
pct_top5 = round(top5_nk / total_nk_papers * 100, 1) if total_nk_papers > 0 else 0

# ── Concepto más frecuente por autor ─────────────────────────────────────────
# Para todos los autores con nk_score > 0, cuál es su concepto dominante
concepto_dominante = defaultdict(int)
for a in autor_stats:
    if a["top_conceptos"]:
        concepto_dominante[a["top_conceptos"][0]["key"]] += 1

# ── Output ────────────────────────────────────────────────────────────────────
out = {
    "meta": {
        "total_autores_min2papers": total_autores,
        "autores_con_nk":           autores_con_nk,
        "autores_dsge_especifico":  autores_dsge,
        "pct_autores_con_nk":       round(autores_con_nk / total_autores * 100, 1) if total_autores > 0 else 0,
        "total_nk_papers":          total_nk_papers,
        "pct_top5_concentracion":   pct_top5,
        "concepto_dominante_dist":  dict(concepto_dominante),
    },
    "top_nk": top_nk,
    "todos": autor_stats,
}

outpath = BASE / "docs/data/author_dsge.json"
json.dump(out, open(outpath, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"✓ {outpath}")

# ── Reporte ───────────────────────────────────────────────────────────────────
print(f"\nAutores con ≥2 papers: {total_autores}")
print(f"Autores que usan vocab NK: {autores_con_nk} ({out['meta']['pct_autores_con_nk']}%)")
print(f"Autores con DSGE explícito: {autores_dsge}")
print(f"Top-5 autores concentran {pct_top5}% de los papers NK")
print(f"\nTop 20 'portadores del toolkit' (por nk_score):")
print(f"{'Autor':<35} {'Papers':>6} {'NK':>4} {'%NK':>6} {'Score':>6} {'1er NK':>7}  Conceptos")
print("-"*90)
for a in top_nk:
    cs = " · ".join(c["label"] for c in a["top_conceptos"][:3])
    print(f"{a['nombre']:<35} {a['total_papers']:>6} {a['n_nk']:>4} {a['pct_nk']:>5.0f}% {a['nk_score']:>6}  {str(a['primer_nk']):>6}  {cs}")
