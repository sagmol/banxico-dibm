"""
10b_temporal_citas.py
----------------------
¿Cambió el patrón de citas antes/después del inflation targeting (2001)?
¿Rehabilitó el Banxico a Minsky post-crisis 2008 como hicieron otros BCs?
Output: docs/data/temporal_citas.json
"""
import re, json, sys, pandas as pd
from pathlib import Path
from collections import defaultdict
sys.stdout.reconfigure(encoding="utf-8")

BASE  = Path(__file__).parent.parent
refs  = pd.read_csv(BASE / "data/processed/referencias_raw.csv")
papers = pd.read_csv(BASE / "data/processed/papers.csv")[["clave","anio"]]

# Join: año del paper que cita
df = refs.merge(papers, left_on="clave_paper", right_on="clave", how="left")
df = df[df["anio"].notna()].copy()
df["anio"] = df["anio"].astype(int)

PERIODOS = [
    ("pre_IT",      1978, 2000, "Pre inflation targeting"),
    ("early_IT",    2001, 2008, "IT consolidado"),
    ("post_crisis", 2009, 2015, "Post-crisis 2008"),
    ("reciente",    2016, 2025, "Reciente"),
]

RE_AUTOR = re.compile(r"^\s*(?:\[\d+\]\s*)?([A-ZÁÉÍÓÚÑÜ][a-záéíóúñü\-\']{1,25})")

def apellido(texto):
    m = RE_AUTOR.match(str(texto).strip())
    return m.group(1) if m else None

por_periodo = []
for pid, a_ini, a_fin, label in PERIODOS:
    sub = df[(df["anio"] >= a_ini) & (df["anio"] <= a_fin)]
    cls = sub[sub["categoria"] != "desconocido"]
    n_papers = sub["clave_paper"].nunique()
    if n_papers == 0: continue

    cat_dist = cls["categoria"].value_counts().to_dict()
    subcat_dist = cls["subcategoria"].value_counts().head(6).to_dict()
    top_jour = (cls[cls["journal_detectado"].notna()]
                .groupby("journal_detectado").size()
                .sort_values(ascending=False).head(5).to_dict())

    apellidos = sub["texto_raw"].dropna().apply(apellido).dropna()
    top_aut = apellidos.value_counts().head(6).to_dict()

    total_cls = len(cls)
    ort = cat_dist.get("ortodoxo", 0) + cat_dist.get("institucional", 0)
    het = cat_dist.get("heterodoxo", 0) + cat_dist.get("estructuralista", 0)

    por_periodo.append({
        "id": pid, "label": label,
        "anio_ini": a_ini, "anio_fin": a_fin,
        "n_papers": n_papers,
        "n_refs": len(sub),
        "n_clasificadas": total_cls,
        "pct_ortodoxo": round(ort / total_cls * 100, 1) if total_cls else 0,
        "pct_heterodoxo": round(het / total_cls * 100, 1) if total_cls else 0,
        "top_journals": [{"j": k, "n": v} for k,v in top_jour.items()],
        "top_autores": [{"a": k, "n": v} for k,v in top_aut.items()],
        "cat_dist": cat_dist,
        "subcat_dist": subcat_dist,
    })

# Por año
por_anio = []
for anio, sub in df.groupby("anio"):
    cls = sub[sub["categoria"] != "desconocido"]
    total = len(cls)
    ort = len(cls[cls["categoria"].isin(["ortodoxo","institucional"])])
    het = len(cls[cls["categoria"].isin(["heterodoxo","estructuralista"])])
    por_anio.append({
        "anio": int(anio),
        "n_papers": sub["clave_paper"].nunique(),
        "n_refs": len(sub),
        "n_cls": total,
        "pct_ort": round(ort/total*100,1) if total else 0,
        "pct_het": round(het/total*100,1) if total else 0,
    })

out = {"por_periodo": por_periodo, "por_anio": sorted(por_anio, key=lambda x: x["anio"])}
json.dump(out, open(BASE/"docs/data/temporal_citas.json","w",encoding="utf-8"), ensure_ascii=False, indent=2)
pd.DataFrame(por_anio).to_csv(BASE/"data/processed/temporal_citas_resumen.csv", index=False, encoding="utf-8-sig")

print("="*65)
print(f"{'Período':<18} {'Papers':>6} {'Refs':>6} {'%Ort':>6} {'%Het':>6}")
print("-"*65)
for p in por_periodo:
    print(f"{p['label']:<18} {p['n_papers']:>6} {p['n_refs']:>6} {p['pct_ortodoxo']:>6.1f}% {p['pct_heterodoxo']:>6.1f}%")
    print(f"  Top autores: {[x['a'] for x in p['top_autores'][:4]]}")
    print(f"  Top journals: {[x['j'] for x in p['top_journals'][:3]]}")
print("="*65)
