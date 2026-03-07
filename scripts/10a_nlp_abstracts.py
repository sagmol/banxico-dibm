"""
10a_nlp_abstracts.py
---------------------
Análisis de vocabulario ortodoxo/heterodoxo en abstracts del corpus completo.
Pregunta: ¿cambió el lenguaje del Banxico con el tiempo?
Output: docs/data/nlp_vocab_periodo.json, nlp_vocab_anio.json
"""
import re, json, sys, pandas as pd
from pathlib import Path
from collections import defaultdict
sys.stdout.reconfigure(encoding="utf-8")

BASE = Path(__file__).parent.parent
papers = pd.read_csv(BASE / "data/processed/papers.csv")

VOCAB_ORTODOXO = [
    "dsge", "general equilibrium", "representative agent", "calvo pricing",
    "output gap", "potential output", "nairu", "natural rate",
    "rational expectations", "microfoundations", "taylor rule",
    "inflation targeting", "inflation expectations", "credibility",
    "forward guidance", "bayesian", "impulse response",
    "new keynesian", "monetary transmission", "nominal rigidities",
    "price stickiness", "optimal monetary policy", "central bank independence",
    "dynamic stochastic", "loss function", "phillips curve",
]

VOCAB_HETERODOXO = [
    "endogenous money", "effective demand", "conflict inflation",
    "markup pricing", "cost-push", "power", "distribution",
    "minsky", "kalecki", "financial instability", "debt deflation",
    "animal spirits", "post-keynesian", "heterodox",
    "functional finance", "chartalism", "monetary circuit",
]

PERIODOS = {
    "pre_IT":      (0,    2000),
    "early_IT":    (2001, 2008),
    "post_crisis": (2009, 2015),
    "reciente":    (2016, 9999),
}

def contar_vocab(texto, lista):
    t = str(texto).lower()
    return [(term, 1) for term in lista if term in t]

papers["texto"] = (papers["resumen_ing"].fillna("") + " " + papers["resumen_esp"].fillna("")).str.strip()
papers = papers[papers["texto"].str.len() > 50].copy()

def get_periodo(anio):
    for nombre, (a, b) in PERIODOS.items():
        if a <= anio <= b:
            return nombre
    return "otro"

papers["periodo"] = papers["anio"].apply(get_periodo)

# Contar por paper
rows = []
for _, p in papers.iterrows():
    hits_ort = contar_vocab(p["texto"], VOCAB_ORTODOXO)
    hits_het = contar_vocab(p["texto"], VOCAB_HETERODOXO)
    rows.append({
        "clave": p["clave"], "anio": p["anio"], "periodo": p["periodo"],
        "n_ort": len(hits_ort), "n_het": len(hits_het),
        "terms_ort": [t for t,_ in hits_ort],
        "terms_het": [t for t,_ in hits_het],
    })
df = pd.DataFrame(rows)
df.to_csv(BASE / "data/processed/papers_nlp.csv", index=False, encoding="utf-8-sig")

# Frecuencia total de cada término
freq_ort = defaultdict(int)
freq_het = defaultdict(int)
for _, r in df.iterrows():
    for t in r["terms_ort"]: freq_ort[t] += 1
    for t in r["terms_het"]: freq_het[t] += 1

top_ort = sorted(freq_ort.items(), key=lambda x: -x[1])[:20]
top_het = sorted(freq_het.items(), key=lambda x: -x[1])

# Por período
por_periodo = []
for nombre in ["pre_IT", "early_IT", "post_crisis", "reciente"]:
    sub = df[df["periodo"] == nombre]
    if len(sub) == 0: continue
    fq = defaultdict(int)
    for _, r in sub.iterrows():
        for t in r["terms_ort"]: fq[t] += 1
    por_periodo.append({
        "periodo": nombre,
        "n_papers": len(sub),
        "prom_ort": round(sub["n_ort"].mean(), 2),
        "prom_het": round(sub["n_het"].mean(), 2),
        "pct_con_vocab_ort": round((sub["n_ort"] > 0).mean() * 100, 1),
        "top_terms": [{"term": t, "freq": c} for t, c in sorted(fq.items(), key=lambda x:-x[1])[:8]],
    })

# Por año
por_anio = []
for anio, sub in df.groupby("anio"):
    por_anio.append({
        "anio": int(anio),
        "n_papers": len(sub),
        "prom_ort": round(sub["n_ort"].mean(), 2),
        "prom_het": round(sub["n_het"].mean(), 2),
    })

out = {
    "total_papers_con_abstract": len(df),
    "top_terminos_ortodoxos": [{"term": t, "freq": c} for t, c in top_ort],
    "top_terminos_heterodoxos": [{"term": t, "freq": c} for t, c in top_het],
    "por_periodo": por_periodo,
    "por_anio": por_anio,
}
(BASE / "docs/data").mkdir(parents=True, exist_ok=True)
json.dump(out, open(BASE / "docs/data/nlp_vocab_periodo.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
json.dump(por_anio,  open(BASE / "docs/data/nlp_vocab_anio.json",    "w", encoding="utf-8"), ensure_ascii=False, indent=2)

print(f"Papers con abstract: {len(df)}")
print(f"\nTOP TÉRMINOS ORTODOXOS:")
for t, c in top_ort: print(f"  {c:>3}x  {t}")
print(f"\nTOP TÉRMINOS HETERODOXOS:")
for t, c in top_het: print(f"  {c:>3}x  {t}")
print(f"\nPOR PERÍODO:")
for p in por_periodo:
    print(f"  {p['periodo']:<14} {p['n_papers']:>3} papers | ort: {p['prom_ort']:.2f} | het: {p['prom_het']:.2f} | {p['pct_con_vocab_ort']}% usan vocab ort")
    print(f"    top: {[x['term'] for x in p['top_terms'][:4]]}")
