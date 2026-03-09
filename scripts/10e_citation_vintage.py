"""
10e_citation_vintage.py
------------------------
Análisis de "edad" de las referencias: ¿el Banxico cita trabajo cada vez más viejo?
Mide la brecha entre el año del paper citante y el año del trabajo citado.

Output: docs/data/citation_vintage.json
"""
import re, json, sys, pandas as pd, numpy as np
from pathlib import Path
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8")

BASE   = Path(__file__).parent.parent
refs   = pd.read_csv(BASE / "data/processed/referencias_raw.csv")
papers = pd.read_csv(BASE / "data/processed/papers.csv")[["clave","anio","decada"]]

PERIODOS = {
    "early_IT":    (2001, 2008),
    "post_crisis": (2009, 2015),
    "reciente":    (2016, 9999),
}
PERIODO_LABELS = {
    "early_IT":    "IT consolidado (2001–08)",
    "post_crisis": "Post-crisis (2009–15)",
    "reciente":    "Reciente (2016–25)",
}
PERIODO_COLORS = {
    "early_IT":    "#4ECDC4",
    "post_crisis": "#FFE66D",
    "reciente":    "#A29BFE",
}

def get_periodo(anio):
    for nombre, (a, b) in PERIODOS.items():
        if a <= anio <= b:
            return nombre
    return None

# ── Merge: añadir año del paper citante ──────────────────────────────────────
refs = refs.merge(papers.rename(columns={"clave":"clave_paper"}), on="clave_paper", how="left")
refs = refs.rename(columns={"anio":"anio_paper"})

# Limpiar anio_citado
refs["anio_citado"] = pd.to_numeric(refs["anio_citado"], errors="coerce")
refs["anio_paper"]  = pd.to_numeric(refs["anio_paper"],  errors="coerce")

valid = refs.dropna(subset=["anio_citado","anio_paper"]).copy()
valid = valid[(valid["anio_citado"] >= 1900) & (valid["anio_citado"] <= 2025)]
valid["edad"] = valid["anio_paper"] - valid["anio_citado"]
valid = valid[valid["edad"] >= 0]  # descartar citas a trabajo futuro (errores OCR)

valid["periodo"] = valid["anio_paper"].apply(get_periodo)
valid_p = valid.dropna(subset=["periodo"])

print(f"Referencias válidas con año: {len(valid)} / {len(refs)}")

# ── Stats globales ────────────────────────────────────────────────────────────
overall = {
    "n_refs":       int(len(valid)),
    "median_age":   round(float(valid["edad"].median()), 1),
    "mean_age":     round(float(valid["edad"].mean()), 1),
    "p25":          round(float(valid["edad"].quantile(.25)), 1),
    "p75":          round(float(valid["edad"].quantile(.75)), 1),
    "anio_citado_median": round(float(valid["anio_citado"].median()), 1),
}

# ── Por período ───────────────────────────────────────────────────────────────
por_periodo = []
for nombre, (a, b) in PERIODOS.items():
    sub = valid_p[valid_p["periodo"] == nombre]
    if len(sub) == 0: continue
    por_periodo.append({
        "periodo":       nombre,
        "label":         PERIODO_LABELS[nombre],
        "color":         PERIODO_COLORS[nombre],
        "n_refs":        int(len(sub)),
        "n_papers":      int(sub["clave_paper"].nunique()),
        "median_age":    round(float(sub["edad"].median()), 1),
        "mean_age":      round(float(sub["edad"].mean()), 1),
        "p25":           round(float(sub["edad"].quantile(.25)), 1),
        "p75":           round(float(sub["edad"].quantile(.75)), 1),
        "anio_citado_median": round(float(sub["anio_citado"].median()), 1),
        # Distribución de edades en bins de 5 años
        "dist_edad": [
            {"bin": int(b2.left), "n": int(n)}
            for b2, n in sub["edad"].value_counts(bins=range(0, 71, 5), sort=False).items()
            if n > 0
        ],
    })

# ── Por año del paper citante ─────────────────────────────────────────────────
por_anio_paper = []
for anio_p, grp in valid_p.groupby("anio_paper"):
    por_anio_paper.append({
        "anio":          int(anio_p),
        "n_refs":        int(len(grp)),
        "median_age":    round(float(grp["edad"].median()), 1),
        "mean_age":      round(float(grp["edad"].mean()), 1),
        "p25":           round(float(grp["edad"].quantile(.25)), 1),
        "p75":           round(float(grp["edad"].quantile(.75)), 1),
        "anio_citado_median": round(float(grp["anio_citado"].median()), 1),
    })
por_anio_paper.sort(key=lambda x: x["anio"])

# ── Distribución acumulada de años citados (para mostrar el "canon") ──────────
# ¿Qué décadas concentran las citas?
canon = []
for decada in range(1960, 2026, 5):
    n = int(((valid["anio_citado"] >= decada) & (valid["anio_citado"] < decada+5)).sum())
    pct = round(n / len(valid) * 100, 1)
    canon.append({"decada": decada, "n": n, "pct": pct})

# Por período: ¿cuánto concentran los "clásicos DSGE" (1995–2010)?
clasicos = {}
for nombre, (a, b) in PERIODOS.items():
    sub = valid_p[valid_p["periodo"] == nombre]
    if len(sub) == 0: continue
    n_clasicos = int(((sub["anio_citado"] >= 1995) & (sub["anio_citado"] <= 2010)).sum())
    pct = round(n_clasicos / len(sub) * 100, 1) if len(sub) > 0 else 0
    clasicos[nombre] = {"n": n_clasicos, "pct": pct, "total": int(len(sub))}

# ── Desglose 3 eras por período (para gráfico apilado) ───────────────────────
# Era 1: pre-1995 (antes del paradigma NK-DSGE)
# Era 2: 1995-2010 (era fundacional NK-DSGE)
# Era 3: post-2010 (literatura reciente)
eras_por_periodo = []
for nombre, (a, b) in PERIODOS.items():
    sub = valid_p[valid_p["periodo"] == nombre]
    if len(sub) == 0: continue
    total = len(sub)
    n_pre95    = int((sub["anio_citado"] < 1995).sum())
    n_dsge     = int(((sub["anio_citado"] >= 1995) & (sub["anio_citado"] <= 2010)).sum())
    n_reciente = int((sub["anio_citado"] > 2010).sum())
    eras_por_periodo.append({
        "periodo": nombre,
        "label":   PERIODO_LABELS[nombre],
        "color":   PERIODO_COLORS[nombre],
        "total":   total,
        "pre95":   {"n": n_pre95,    "pct": round(n_pre95/total*100, 1)},
        "dsge":    {"n": n_dsge,     "pct": round(n_dsge/total*100, 1)},
        "post10":  {"n": n_reciente, "pct": round(n_reciente/total*100, 1)},
    })

# ── Top journals en citas post-2010 del período reciente ─────────────────────
# Para visualizar autocitación: Banxico WP aparece como 2do journal más citado
rec_post10 = valid_p[
    (valid_p["periodo"] == "reciente") & (valid_p["anio_citado"] > 2010)
].copy()

BANXICO_JOURNALS = {"banco de méxico wp", "banxico wp", "banco de mexico wp"}
top_journals_raw = rec_post10["journal_detectado"].dropna().value_counts().head(15)
top_journals_post10 = []
for journal, n in top_journals_raw.items():
    pct = round(n / len(rec_post10) * 100, 1)
    es_banxico = any(b in journal.lower() for b in BANXICO_JOURNALS)
    top_journals_post10.append({
        "journal":    journal,
        "n":          int(n),
        "pct":        pct,
        "autocita":   es_banxico,
    })

# ── Output ────────────────────────────────────────────────────────────────────
out = {
    "overall":              overall,
    "por_periodo":          por_periodo,
    "por_anio_paper":       por_anio_paper,
    "canon_quinquenal":     canon,
    "clasicos_dsge_pct":    clasicos,
    "eras_por_periodo":     eras_por_periodo,
    "top_journals_post10":  top_journals_post10,
}
outpath = BASE / "docs/data/citation_vintage.json"
json.dump(out, open(outpath, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"✓ {outpath}")

# ── Reporte ───────────────────────────────────────────────────────────────────
print(f"\nEdad mediana global: {overall['median_age']} años")
print(f"Año citado mediano: {overall['anio_citado_median']}")
print(f"\nPor período:")
for p in por_periodo:
    print(f"  {p['label']:<30} | mediana edad: {p['median_age']:>5} años | año citado mediano: {p['anio_citado_median']:.0f}")
    print(f"    Clásicos DSGE 1995-2010: {clasicos[p['periodo']]['pct']}% de sus citas")
print(f"\nDistribución del canon (qué años concentran las citas):")
for c in canon:
    bar = "█" * int(c["pct"] * 2)
    print(f"  {c['decada']}–{c['decada']+4}  {bar:<30} {c['pct']}%  (n={c['n']})")
