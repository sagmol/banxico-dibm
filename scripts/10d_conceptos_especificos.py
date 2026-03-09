"""
10d_conceptos_especificos.py
-----------------------------
Rastreo de conceptos teóricos específicos en abstracts por año.
Pregunta: ¿cuándo llegó cada pieza del toolkit NK-DSGE al Banxico?

Output: docs/data/nlp_conceptos_anio.json
"""
import re, json, sys, pandas as pd
from pathlib import Path
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8")

BASE = Path(__file__).parent.parent
papers = pd.read_csv(BASE / "data/processed/papers.csv")

# ── Conceptos y sus términos de búsqueda ─────────────────────────────────────
CONCEPTOS = {
    "dsge": [
        "dsge", "dynamic stochastic general equilibrium", "dynamic stochastic",
    ],
    "inflation_exp": [
        "inflation expectations", "inflation expectation",
        "expectativas de inflación", "expectativas inflacionarias",
        "inflationary expectations", "inflation anchoring",
    ],
    "taylor_rule": [
        "taylor rule", "taylor principle", "taylor-type rule",
        "taylor reaction", "regla de taylor", "interest rate rule",
    ],
    "calvo": [
        "calvo", "staggered prices", "staggered price",
        "price stickiness", "sticky prices", "sticky price",
        "nominal rigidities", "nominal rigidity", "price rigidity",
    ],
    "new_keynesian": [
        "new keynesian", "new-keynesian", "nk model",
        "nkpc", "new keynesian phillips", "new-keynesian phillips",
    ],
    "output_gap": [
        "output gap", "output-gap",
        "brecha del producto", "brecha de producto",
        "production gap",
    ],
    "financial_frictions": [
        "financial frictions", "financial friction",
        "credit frictions", "financial accelerator",
        "credit conditions", "credit market frictions",
        "credit constraints", "collateral constraint",
    ],
    "rational_exp": [
        "rational expectations", "rational expectation",
        "expectativas racionales", "model-consistent expectations",
        "model consistent expectations",
    ],
    "phillips_curve": [
        "phillips curve", "phillips-curve",
        "curva de phillips", "phillips relation",
    ],
    "bayesian": [
        "bayesian", "bayesian estimation", "bayesian inference",
        "bayes factor", "posterior distribution", "prior distribution",
    ],
    "inflation_targeting": [
        "inflation targeting", "inflation target", "inflation-targeting",
        "meta de inflación", "objetivo de inflación", "inflation target framework",
        "it framework", "price stability mandate",
    ],
}

LABELS = {
    "dsge":               "DSGE",
    "inflation_exp":      "Inflation expectations",
    "taylor_rule":        "Taylor rule",
    "calvo":              "Calvo / sticky prices",
    "new_keynesian":      "New Keynesian",
    "output_gap":         "Output gap",
    "financial_frictions":"Financial frictions",
    "rational_exp":       "Rational expectations",
    "phillips_curve":     "Phillips curve",
    "bayesian":           "Bayesian",
    "inflation_targeting":"Inflation targeting",
}

COLORS = {
    "dsge":               "#FF6B6B",
    "inflation_exp":      "#4ECDC4",
    "taylor_rule":        "#FFE66D",
    "calvo":              "#FD79A8",
    "new_keynesian":      "#74B9FF",
    "output_gap":         "#A29BFE",
    "financial_frictions":"#55EFC4",
    "rational_exp":       "#FDCB6E",
    "phillips_curve":     "#E17055",
    "bayesian":           "#6CB4F5",
    "inflation_targeting":"#FF9F43",
}

# ── Preparar textos ───────────────────────────────────────────────────────────
papers["texto"] = (
    papers["resumen_ing"].fillna("") + " " + papers["resumen_esp"].fillna("")
).str.strip().str.lower()
papers = papers[papers["texto"].str.len() > 50].copy()


def tiene_concepto(texto, terminos):
    return any(t in texto for t in terminos)


# ── Por año ───────────────────────────────────────────────────────────────────
por_anio = []
for anio, grp in papers.groupby("anio"):
    n = len(grp)
    entry = {"anio": int(anio), "n_papers": n, "pct": {}}
    for clave, terminos in CONCEPTOS.items():
        hits = grp["texto"].apply(lambda t: tiene_concepto(t, terminos)).sum()
        entry["pct"][clave] = round(hits / n * 100, 1)
    por_anio.append(entry)

# ── Rolling 3 años (suavizado) ────────────────────────────────────────────────
# Solo para años con >= 3 papers en la ventana
anios_idx = {r["anio"]: i for i, r in enumerate(por_anio)}

def rolling_avg(anio, clave, ventana=3):
    vals, pesos = [], []
    for delta in range(-(ventana//2), ventana//2 + 1):
        a = anio + delta
        if a in anios_idx:
            r = por_anio[anios_idx[a]]
            vals.append(r["pct"][clave])
            pesos.append(r["n_papers"])
    if not vals: return None
    total = sum(pesos)
    return round(sum(v * p for v, p in zip(vals, pesos)) / total, 1)

for entry in por_anio:
    entry["smooth"] = {}
    for clave in CONCEPTOS:
        entry["smooth"][clave] = rolling_avg(entry["anio"], clave)

# ── Stats globales por concepto ───────────────────────────────────────────────
stats_por_concepto = {}
for clave, terminos in CONCEPTOS.items():
    hits = papers["texto"].apply(lambda t: tiene_concepto(t, terminos))
    n_total = len(papers)
    n_hits  = hits.sum()
    # Primer año de aparición
    papers_hits = papers[hits]
    primer_anio = int(papers_hits["anio"].min()) if len(papers_hits) else None
    stats_por_concepto[clave] = {
        "label":       LABELS[clave],
        "color":       COLORS[clave],
        "total_papers": int(n_hits),
        "pct_corpus":  round(n_hits / n_total * 100, 1),
        "primer_anio": primer_anio,
    }

# ── Output ────────────────────────────────────────────────────────────────────
out = {
    "meta": {
        "total_papers": len(papers),
        "conceptos": LABELS,
        "colores":   COLORS,
    },
    "stats": stats_por_concepto,
    "por_anio": por_anio,
}

outpath = BASE / "docs/data/nlp_conceptos_anio.json"
json.dump(out, open(outpath, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"✓ {outpath}")

# ── Reporte terminal ──────────────────────────────────────────────────────────
print(f"\nCorpus: {len(papers)} papers con abstract\n")
print(f"{'Concepto':<25} {'Total':>6}  {'% corpus':>9}  {'Primer año':>11}")
print("-" * 58)
for clave, s in sorted(stats_por_concepto.items(), key=lambda x: -x[1]["total_papers"]):
    print(f"{s['label']:<25} {s['total_papers']:>6}  {s['pct_corpus']:>8.1f}%  {str(s['primer_anio']):>11}")

print("\nPor año (solo los que tienen ≥1 hit en algún concepto):")
for r in por_anio:
    activos = {k: v for k, v in r["pct"].items() if v > 0}
    if activos:
        top = sorted(activos.items(), key=lambda x: -x[1])[:3]
        print(f"  {r['anio']}  n={r['n_papers']:>3}  " + "  ".join(f"{LABELS[k]}:{v:.0f}%" for k,v in top))
