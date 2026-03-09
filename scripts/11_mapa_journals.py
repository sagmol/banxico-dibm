"""
11_mapa_journals.py
--------------------
Asigna país/región de origen editorial a cada journal detectado en las
referencias del corpus DIBM. Genera journals_geo.json para el mapa D3.

Criterio: país de la sociedad/institución académica que publica el journal
(no el país del publisher comercial como Elsevier/Springer).
"""
import json, sys, pandas as pd
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

BASE = Path(__file__).parent.parent
refs = pd.read_csv(BASE / "data/processed/referencias_raw.csv")

# ── Lookup: journal → (country_code, country_name, region, ciudad) ────────────
# Región: USA / UK / EU / INTL / LATAM / Canada / Other
GEO = {
    # ─── USA ────────────────────────────────────────────────────────────────
    "American Economic Review":              ("US","United States","USA","Nashville/Pittsburgh"),
    "Journal of Monetary Economics":         ("US","United States","USA","Rochester NY"),
    "Econometrica":                          ("US","United States","USA","Evanston IL"),
    "Quarterly Journal of Economics":        ("US","United States","USA","Cambridge MA"),
    "Journal of Political Economy":          ("US","United States","USA","Chicago IL"),
    "Federal Reserve":                       ("US","United States","USA","Washington DC"),
    "Journal of Money, Credit and Banking":  ("US","United States","USA","Columbus OH"),
    "Journal of Econometrics":               ("US","United States","USA","Evanston IL"),
    "Journal of International Economics":    ("US","United States","USA","New Haven CT"),
    "Journal of Business & Economic Statistics": ("US","United States","USA","Washington DC"),
    "NBER Working Paper":                    ("US","United States","USA","Cambridge MA"),
    "Journal of Finance":                    ("US","United States","USA","Chicago IL"),
    "Review of Economics and Statistics":    ("US","United States","USA","Cambridge MA"),
    "Libro (Princeton University Press)":    ("US","United States","USA","Princeton NJ"),
    "Journal of Macroeconomics":             ("US","United States","USA","Baton Rouge LA"),
    "AEJ: Macroeconomics":                   ("US","United States","USA","Nashville/Pittsburgh"),
    "World Bank":                            ("US","United States","INTL","Washington DC"),
    "Brookings Papers on Economic Activity": ("US","United States","USA","Washington DC"),
    "Journal of Financial Economics":        ("US","United States","USA","Rochester NY"),
    "Journal of Economic Perspectives":      ("US","United States","USA","Nashville/Pittsburgh"),
    "Journal of Economic Literature":        ("US","United States","USA","Nashville/Pittsburgh"),
    "Carnegie-Rochester Conference Series":  ("US","United States","USA","Pittsburgh PA"),
    "Journal of Development Economics":      ("US","United States","USA","Evanston IL"),
    "Review of Financial Studies":           ("US","United States","USA","Oxford OH"),
    "NBER Macroeconomics Annual":            ("US","United States","USA","Cambridge MA"),
    "Journal of Economic Theory":            ("US","United States","USA","New Haven CT"),
    "Econometric Theory":                    ("US","United States","USA","Evanston IL"),
    "Econometric Reviews":                   ("US","United States","USA","New York NY"),
    "Journal of Financial Intermediation":   ("US","United States","USA","Philadelphia PA"),
    "Journal of Banking and Finance":        ("US","United States","USA","Philadelphia PA"),
    "Journal of International Money and Finance": ("US","United States","USA","Charlottesville VA"),
    "International Journal of Central Banking":   ("US","United States","USA","Washington DC"),
    "Libro (Wiley)":                         ("US","United States","USA","Hoboken NJ"),
    "Libro (Elsevier)":                      ("US","United States","USA","Philadelphia PA"),
    "Libro (MIT Press)":                     ("US","United States","USA","Cambridge MA"),
    "Libro (McGraw-Hill)":                   ("US","United States","USA","New York NY"),
    "IMF Working Paper":                     ("US","United States","INTL","Washington DC"),
    "IMF Staff Papers":                      ("US","United States","INTL","Washington DC"),
    "Journal of Economic Dynamics and Control": ("US","United States","USA","Amsterdam/US editorial"),
    # ─── UK ─────────────────────────────────────────────────────────────────
    "Economica":                             ("GB","United Kingdom","UK","London"),
    "Economic Journal":                      ("GB","United Kingdom","UK","London"),
    "Review of Economic Studies":            ("GB","United Kingdom","UK","Oxford"),
    "Economics Letters":                     ("GB","United Kingdom","UK","London"),
    "Journal of Applied Econometrics":       ("GB","United Kingdom","UK","Chichester"),
    "Economic Policy":                       ("GB","United Kingdom","UK","London/Paris"),
    "Bank of England":                       ("GB","United Kingdom","UK","London"),
    "Oxford Bulletin of Economics and Statistics": ("GB","United Kingdom","UK","Oxford"),
    "Libro (Oxford University Press)":       ("GB","United Kingdom","UK","Oxford"),
    "Libro (Cambridge University Press)":    ("GB","United Kingdom","UK","Cambridge"),
    # ─── EU ─────────────────────────────────────────────────────────────────
    "ECB Working Paper":                     ("DE","Germany","EU","Frankfurt"),
    "European Economic Review":              ("BE","Belgium","EU","Brussels"),
    "Journal of the European Economic Association": ("DE","Germany","EU","Frankfurt"),
    "Libro (North-Holland)":                 ("NL","Netherlands","EU","Amsterdam"),
    "Libro (Springer)":                      ("DE","Germany","EU","Berlin"),
    "Scandinavian Journal of Economics":     ("SE","Sweden","EU","Stockholm"),
    # ─── Switzerland / BIS ──────────────────────────────────────────────────
    "BIS Working Paper":                     ("CH","Switzerland","INTL","Basel"),
    # ─── Canada ─────────────────────────────────────────────────────────────
    "Bank of Canada":                        ("CA","Canada","Canada","Ottawa"),
    # ─── Mexico / LATAM ─────────────────────────────────────────────────────
    "Banco de México WP":                    ("MX","Mexico","LATAM","Ciudad de México"),
    "Monetaria (CEMLA)":                     ("MX","Mexico","LATAM","Ciudad de México"),
    "El Trimestre Económico":                ("MX","Mexico","LATAM","Ciudad de México"),
    "Libro (Fondo de Cultura Económica)":    ("MX","Mexico","LATAM","Ciudad de México"),
    # ─── Libro (Univ Chicago Press) — USA ───────────────────────────────────
    "Libro (University Of Chicago Press)":   ("US","United States","USA","Chicago IL"),
    "Libro (University of Chicago Press)":   ("US","United States","USA","Chicago IL"),
    "Libro (Mit Press)":                     ("US","United States","USA","Cambridge MA"),
    "Libro (Mcgraw-Hill)":                   ("US","United States","USA","New York NY"),
}

REGION_COLORS = {
    "USA":    "#4ECDC4",
    "UK":     "#74B9FF",
    "EU":     "#A29BFE",
    "INTL":   "#FFE66D",
    "LATAM":  "#FD79A8",
    "Canada": "#55EFC4",
    "Other":  "#7d8590",
}

# ── Contar citas por journal ──────────────────────────────────────────────────
jcounts = refs["journal_detectado"].value_counts()
total_identificadas = jcounts.sum()

# ── Asignar geografía ─────────────────────────────────────────────────────────
rows = []
n_mapeadas = 0
for journal, n in jcounts.items():
    if journal in GEO:
        cc, cname, region, ciudad = GEO[journal]
        n_mapeadas += n
        rows.append({
            "journal":  journal,
            "n":        int(n),
            "cc":       cc,
            "pais":     cname,
            "region":   region,
            "ciudad":   ciudad,
        })
    # else: skip (desconocido o sin mapeo)

# ── Agregar por país ──────────────────────────────────────────────────────────
from collections import defaultdict
por_pais = defaultdict(lambda: {"n":0, "region":"Other", "journals":[]})
for r in rows:
    por_pais[r["cc"]]["n"]       += r["n"]
    por_pais[r["cc"]]["pais"]     = r["pais"]
    por_pais[r["cc"]]["region"]   = r["region"]
    por_pais[r["cc"]]["ciudad"]   = r.get("ciudad","")
    por_pais[r["cc"]]["journals"].append({"journal":r["journal"],"n":r["n"]})

# Ordenar journals dentro de cada país
for cc in por_pais:
    por_pais[cc]["journals"].sort(key=lambda x: -x["n"])

# ── Coordenadas aproximadas por país (para el mapa) ───────────────────────────
COORDS = {
    "US": [37.09, -95.71],
    "GB": [55.38, -3.44],
    "DE": [51.17, 10.45],
    "BE": [50.50, 4.47],
    "NL": [52.13, 5.29],
    "SE": [60.13, 18.64],
    "CH": [46.82, 8.23],
    "CA": [56.13, -106.35],
    "MX": [23.63, -102.55],
    "FR": [46.23, 2.21],
}

paises_list = []
for cc, v in sorted(por_pais.items(), key=lambda x: -x[1]["n"]):
    coords = COORDS.get(cc, [0, 0])
    paises_list.append({
        "cc":       cc,
        "pais":     v["pais"],
        "region":   v["region"],
        "color":    REGION_COLORS.get(v["region"], "#7d8590"),
        "n":        v["n"],
        "pct":      round(v["n"] / n_mapeadas * 100, 1),
        "lat":      coords[0],
        "lng":      coords[1],
        "journals": v["journals"][:10],  # top 10 por país
    })

# ── Resumen por región ────────────────────────────────────────────────────────
por_region = defaultdict(int)
for r in rows:
    por_region[r["region"]] += r["n"]
region_list = [
    {"region": k, "n": v, "pct": round(v/n_mapeadas*100,1), "color": REGION_COLORS[k]}
    for k, v in sorted(por_region.items(), key=lambda x: -x[1])
]

# ── Output ────────────────────────────────────────────────────────────────────
out = {
    "total_refs":        int(jcounts.sum()),
    "refs_mapeadas":     int(n_mapeadas),
    "pct_mapeadas":      round(n_mapeadas / jcounts.sum() * 100, 1),
    "por_pais":          paises_list,
    "por_region":        region_list,
    "region_colors":     REGION_COLORS,
}

outpath = BASE / "docs/data/journals_geo.json"
json.dump(out, open(outpath, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"✓ {outpath}")
print(f"\nTotal refs con journal: {jcounts.sum()}")
print(f"Mapeadas geográficamente: {n_mapeadas} ({n_mapeadas/jcounts.sum()*100:.1f}%)")
print(f"\nPor región:")
for r in region_list:
    bar = "█" * int(r["pct"] / 2)
    print(f"  {r['region']:<8} {bar:<30} {r['pct']:5.1f}%  (n={r['n']})")
print(f"\nPor país (top 10):")
for p in paises_list[:10]:
    print(f"  {p['cc']}  {p['pais']:<20} {p['pct']:5.1f}%  (n={p['n']})")
    for j in p["journals"][:3]:
        print(f"      {j['n']:3d}  {j['journal']}")
