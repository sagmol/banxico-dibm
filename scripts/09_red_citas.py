"""
09_red_citas.py
---------------
Genera los datos JSON para las visualizaciones D3:
  1. Red de co-citación de autores (nodes + links)
  2. Red de co-citación de journals (nodes + links)
  3. Stats agregadas para el Spotify Wrapped

Outputs en docs/data/ (accesibles desde GitHub Pages):
  autores_red.json
  journals_red.json
  orthodoxy_stats.json
"""

import re, json, sys, itertools
import pandas as pd
from pathlib import Path
from collections import defaultdict
sys.stdout.reconfigure(encoding="utf-8")

BASE      = Path(__file__).parent.parent
REFS_CSV  = BASE / "data/processed/referencias_raw.csv"
AUTH_CSV  = BASE / "data/processed/autores_citados.csv"
JOUR_CSV  = BASE / "data/processed/referencias_journals.csv"
OUT_DIR   = BASE / "docs/data"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Corrientes → color ────────────────────────────────────────────────────────
COLOR = {
    "new_keynesian":   "#4ECDC4",
    "econometria":     "#FFE66D",
    "monetarista":     "#FF6B6B",
    "nueva_clasica":   "#A29BFE",
    "rbc":             "#55EFC4",
    "keynesiano_orig": "#FD79A8",
    "heterodoxo":      "#E17055",
    "estructuralista": "#00B894",
    "no_clasificado":  "#636e72",
}

AUTORES_CANON = {
    "friedman":   ("monetarista",     "Milton Friedman"),
    "phelps":     ("monetarista",     "Edmund Phelps"),
    "lucas":      ("nueva_clasica",   "Robert Lucas"),
    "sargent":    ("nueva_clasica",   "Thomas Sargent"),
    "barro":      ("nueva_clasica",   "Robert Barro"),
    "kydland":    ("rbc",             "Finn Kydland"),
    "prescott":   ("rbc",             "Edward Prescott"),
    "woodford":   ("new_keynesian",   "Michael Woodford"),
    "galí":       ("new_keynesian",   "Jordi Galí"),
    "gali":       ("new_keynesian",   "Jordi Galí"),
    "gertler":    ("new_keynesian",   "Mark Gertler"),
    "clarida":    ("new_keynesian",   "Richard Clarida"),
    "blanchard":  ("new_keynesian",   "Olivier Blanchard"),
    "mankiw":     ("new_keynesian",   "N. Gregory Mankiw"),
    "taylor":     ("new_keynesian",   "John Taylor"),
    "svensson":   ("new_keynesian",   "Lars Svensson"),
    "bernanke":   ("new_keynesian",   "Ben Bernanke"),
    "christiano": ("new_keynesian",   "Lawrence Christiano"),
    "eichenbaum": ("new_keynesian",   "Martin Eichenbaum"),
    "smets":      ("new_keynesian",   "Frank Smets"),
    "wouters":    ("new_keynesian",   "Rafael Wouters"),
    "calvo":      ("new_keynesian",   "Guillermo Calvo"),
    "romer":      ("new_keynesian",   "David Romer"),
    "rotemberg":  ("new_keynesian",   "Julio Rotemberg"),
    "ireland":    ("new_keynesian",   "Peter Ireland"),
    "engle":      ("econometria",     "Robert Engle"),
    "granger":    ("econometria",     "Clive Granger"),
    "hamilton":   ("econometria",     "James Hamilton"),
    "sims":       ("econometria",     "Christopher Sims"),
    "stock":      ("econometria",     "James Stock"),
    "watson":     ("econometria",     "Mark Watson"),
    "diebold":    ("econometria",     "Francis Diebold"),
    "hodrick":    ("econometria",     "Robert Hodrick"),
    "dickey":     ("econometria",     "David Dickey"),
    "johansen":   ("econometria",     "Søren Johansen"),
    "keynes":     ("keynesiano_orig", "John Maynard Keynes"),
    "kalecki":    ("heterodoxo",      "Michał Kalecki"),
    "minsky":     ("heterodoxo",      "Hyman Minsky"),
    "lavoie":     ("heterodoxo",      "Marc Lavoie"),
    "godley":     ("heterodoxo",      "Wynne Godley"),
    "kaldor":     ("heterodoxo",      "Nicholas Kaldor"),
    "davidson":   ("heterodoxo",      "Paul Davidson"),
    "robinson":   ("heterodoxo",      "Joan Robinson"),
    "prebisch":   ("estructuralista", "Raúl Prebisch"),
    "ros":        ("estructuralista", "Jaime Ros"),
}

RE_AUTOR = re.compile(
    r"^\s*(?:\[\d+\]\s*)?"
    r"([A-ZÁÉÍÓÚÑÜÄÖ][a-záéíóúñüäö\-\']{1,25})"
)

def extraer_apellido(texto):
    m = RE_AUTOR.match(str(texto).strip())
    return m.group(1).strip() if m else None

# ═══════════════════════════════════════════════════════════════════════════════
# 1. RED DE AUTORES
# ═══════════════════════════════════════════════════════════════════════════════
print("Construyendo red de autores...")
refs = pd.read_csv(REFS_CSV)

# Autores por paper
paper_autores = defaultdict(set)
for _, row in refs.iterrows():
    ap = extraer_apellido(row["texto_raw"])
    if ap and len(ap) > 2:
        paper_autores[row["clave_paper"]].add(ap.lower())

# Conteo global de citas por autor
conteo_global = defaultdict(int)
for autores in paper_autores.values():
    for a in autores:
        conteo_global[a] += 1

# Filtro: solo autores con ≥3 citas
autores_filtrados = {a for a, n in conteo_global.items() if n >= 3}

# Co-citación: pares de autores en el mismo paper
cooc = defaultdict(int)
for autores in paper_autores.values():
    validos = autores & autores_filtrados
    for a, b in itertools.combinations(sorted(validos), 2):
        cooc[(a, b)] += 1

# Nodes
nodes_autores = []
id_map = {}
for i, apellido in enumerate(sorted(autores_filtrados)):
    clave = apellido.lower()
    corriente, nombre = AUTORES_CANON.get(clave, ("no_clasificado", apellido.title()))
    # Desduplicar galí/gali
    if clave == "galí":
        corriente, nombre = "new_keynesian", "Jordi Galí"
    nodes_autores.append({
        "id": i,
        "apellido": apellido.title(),
        "nombre": nombre,
        "corriente": corriente,
        "color": COLOR.get(corriente, COLOR["no_clasificado"]),
        "citas": conteo_global[apellido.lower()],
    })
    id_map[apellido.lower()] = i

# Links (umbral: co-citados en ≥2 papers)
links_autores = []
for (a, b), peso in cooc.items():
    if peso >= 2 and a in id_map and b in id_map:
        links_autores.append({
            "source": id_map[a],
            "target": id_map[b],
            "value": peso,
        })

json.dump(
    {"nodes": nodes_autores, "links": links_autores},
    open(OUT_DIR / "autores_red.json", "w", encoding="utf-8"),
    ensure_ascii=False, indent=2
)
print(f"  Nodos: {len(nodes_autores)} | Links: {len(links_autores)}")

# ═══════════════════════════════════════════════════════════════════════════════
# 2. RED DE JOURNALS
# ═══════════════════════════════════════════════════════════════════════════════
print("Construyendo red de journals...")

COLOR_JOUR = {
    "tier1_generalist":  "#E84393",
    "macro_monetario":   "#4ECDC4",
    "econometria":       "#FFE66D",
    "finanzas":          "#A29BFE",
    "internacional":     "#74B9FF",
    "otros_mainstream":  "#81ECEC",
    "libro_mainstream":  "#B2BEC3",
    "wp_banxico":        "#FD79A8",
    "wp_multilateral":   "#FDCB6E",
    "wp_bc_avanzado":    "#E17055",
    "wp_bc_latam":       "#00B894",
    "cepal":             "#55EFC4",
    "heterodoxo":        "#D63031",
    "desconocido":       "#2D3436",
}

# Journals conocidos por paper
paper_journals = defaultdict(set)
refs_cls = refs[refs["journal_detectado"].notna() & (refs["categoria"] != "desconocido")]
for _, row in refs_cls.iterrows():
    paper_journals[row["clave_paper"]].add(row["journal_detectado"])

# Conteo
conteo_jour = defaultdict(int)
for js in paper_journals.values():
    for j in js:
        conteo_jour[j] += 1

journals_filtrados = {j for j, n in conteo_jour.items() if n >= 3}

# Metadata de journals
jour_meta = {}
for _, row in refs_cls.iterrows():
    j = row["journal_detectado"]
    if j not in jour_meta:
        jour_meta[j] = {"subcategoria": row["subcategoria"], "categoria": row["categoria"]}

# Co-ocurrencia de journals
cooc_jour = defaultdict(int)
for js in paper_journals.values():
    validos = js & journals_filtrados
    for a, b in itertools.combinations(sorted(validos), 2):
        cooc_jour[(a, b)] += 1

# Nodes journals
nodes_jour, id_jour = [], {}
for i, j in enumerate(sorted(journals_filtrados)):
    meta = jour_meta.get(j, {"subcategoria": "desconocido", "categoria": "desconocido"})
    subcat = meta["subcategoria"]
    nodes_jour.append({
        "id": i,
        "nombre": j,
        "subcategoria": subcat,
        "categoria": meta["categoria"],
        "color": COLOR_JOUR.get(subcat, "#636e72"),
        "citas": conteo_jour[j],
    })
    id_jour[j] = i

# Links journals
links_jour = []
for (a, b), peso in cooc_jour.items():
    if peso >= 2 and a in id_jour and b in id_jour:
        links_jour.append({"source": id_jour[a], "target": id_jour[b], "value": peso})

json.dump(
    {"nodes": nodes_jour, "links": links_jour},
    open(OUT_DIR / "journals_red.json", "w", encoding="utf-8"),
    ensure_ascii=False, indent=2
)
print(f"  Nodos: {len(nodes_jour)} | Links: {len(links_jour)}")

# ═══════════════════════════════════════════════════════════════════════════════
# 3. STATS PARA SPOTIFY WRAPPED
# ═══════════════════════════════════════════════════════════════════════════════
print("Calculando stats...")

total_refs = len(refs)
cls = refs[refs["categoria"] != "desconocido"]
total_cls = len(cls)

# Por categoría grande
cat_counts = cls["categoria"].value_counts().to_dict()
ortodoxo_n = cat_counts.get("ortodoxo", 0)
inst_n      = cat_counts.get("institucional", 0)
het_n       = cat_counts.get("heterodoxo", 0) + cat_counts.get("estructuralista", 0)

pct_ort = round((ortodoxo_n + inst_n) / total_cls * 100, 1)
pct_het = round(het_n / total_cls * 100, 1)

# Top 10 journals
jour_df  = pd.read_csv(JOUR_CSV)
top_jour = jour_df.head(10)[["journal_detectado","subcategoria","n_citas"]].to_dict("records")

# Top autores canónicos
auth_df  = pd.read_csv(AUTH_CSV)
top_auth = auth_df[auth_df["corriente"] != "no_clasificado"].head(15).to_dict("records")

# Autores totales únicos detectados
n_autores_unicos = len(auth_df[auth_df["n_citas"] >= 2])

# Años cubiertos
años = refs["anio_citado"].dropna().astype(int)

# Por corriente de autores
auth_cls = auth_df[auth_df["corriente"] != "no_clasificado"]
por_corriente = auth_cls.groupby("corriente")["n_citas"].sum().sort_values(ascending=False)
por_corriente_d = por_corriente.to_dict()
total_corr = sum(por_corriente_d.values())

# Papers por año (para timeline)
papers_df  = pd.read_csv(BASE / "data/processed/papers.csv")
jel_df     = pd.read_csv(BASE / "data/processed/paper_jel.csv")
inf_claves = jel_df[jel_df["jel_code"].str.startswith(("E3","E5"))]["clave_paper"].unique()
inf_papers = papers_df[papers_df["clave"].isin(inf_claves)]
por_anio   = inf_papers.groupby("anio").size().reset_index(name="n")

stats = {
    "total_refs":          total_refs,
    "total_clasificadas":  total_cls,
    "pct_clasificado":     round(total_cls / total_refs * 100, 1),
    "pct_ortodoxo_inst":   pct_ort,
    "pct_heterodoxo":      pct_het,
    "n_citas_ortodoxo":    ortodoxo_n + inst_n,
    "n_citas_heterodoxo":  het_n,
    "n_autores_unicos":    n_autores_unicos,
    "anio_min_citado":     int(años.min()),
    "anio_max_citado":     int(años.max()),
    "autor_top":           top_auth[0]["nombre_canonico"] if top_auth else "",
    "autor_top_citas":     int(top_auth[0]["n_citas"]) if top_auth else 0,
    "top_journals":        top_jour,
    "top_autores":         top_auth,
    "corrientes":          [
        {"corriente": k, "citas": int(v), "pct": round(v/total_corr*100,1)}
        for k, v in por_corriente_d.items()
    ],
    "papers_por_anio":     por_anio.to_dict("records"),
    "n_papers_inflacion":  len(inf_papers),
}

json.dump(stats, open(OUT_DIR / "orthodoxy_stats.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)

print(f"\n{'='*50}")
print(f"  JSONs guardados en {OUT_DIR}")
print(f"  ortodoxo+institucional : {pct_ort}%")
print(f"  heterodoxo             : {pct_het}%")
print(f"  autor más citado       : {stats['autor_top']} ({stats['autor_top_citas']}x)")
print(f"{'='*50}")
