"""
gen_coautoria_json.py  —  Genera docs/data/coautoria_red.json
Red de coautoría DIBM Banxico.

Uso:
  /c/Users/USER/anaconda3/python.exe scripts/gen_coautoria_json.py

Nodos: autores con >= 2 papers
Links: pares que co-autoron >= 1 paper (value = N° papers juntos)
"""
import json, itertools, sys
from pathlib import Path
import pandas as pd

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE    = Path(__file__).resolve().parent.parent
PA_CSV  = BASE / "data" / "processed" / "paper_authors.csv"
PP_CSV  = BASE / "data" / "processed" / "papers.csv"
OUT_DIR = BASE / "docs" / "data"
OUT_JSON = OUT_DIR / "coautoria_red.json"

# ── Load ───────────────────────────────────────────────────────────────────────
pa = pd.read_csv(PA_CSV)
pp = pd.read_csv(PP_CSV)

print(f"paper_authors: {len(pa)} rows, {pa['autor_id'].nunique()} unique authors, {pa['clave_paper'].nunique()} papers")

# Paper metadata: clave -> dict
paper_meta = {}
for _, row in pp.iterrows():
    clave  = str(row["clave"]).strip()
    titulo = str(row.get("titulo_ing") or row.get("titulo_esp") or clave)
    url    = str(row.get("url_pdf_ing") or "")
    paper_meta[clave] = {
        "clave":  clave,
        "anio":   int(row["anio"]) if pd.notna(row.get("anio")) else None,
        "titulo": titulo[:55] + ("\u2026" if len(titulo) > 55 else ""),
        "url":    url if url != "nan" else ""
    }

# ── Author paper lists ─────────────────────────────────────────────────────────
author_papers = {}   # autor_id -> set of clave_paper
author_name   = {}   # autor_id -> presentacion

for _, row in pa.iterrows():
    aid   = str(row["autor_id"])
    clave = str(row["clave_paper"]).strip()
    name  = str(row.get("presentacion") or aid)
    if aid not in author_papers:
        author_papers[aid] = set()
        author_name[aid]   = name
    author_papers[aid].add(clave)

# Qualified: >= 2 papers
qualified = {aid for aid, pset in author_papers.items() if len(pset) >= 2}
print(f"Authors with >= 2 papers: {len(qualified)}")

# ── Co-authorship edges ────────────────────────────────────────────────────────
# paper -> list of qualified authors
paper_qa = {}
for _, row in pa.iterrows():
    aid   = str(row["autor_id"])
    clave = str(row["clave_paper"]).strip()
    if aid not in qualified: continue
    paper_qa.setdefault(clave, [])
    if aid not in paper_qa[clave]:
        paper_qa[clave].append(aid)

edge_weight = {}
for clave, authors in paper_qa.items():
    for a, b in itertools.combinations(sorted(authors), 2):
        key = (a, b)
        edge_weight[key] = edge_weight.get(key, 0) + 1

print(f"Co-authorship edges: {len(edge_weight)}")

# ── Degree ─────────────────────────────────────────────────────────────────────
degree = {aid: 0 for aid in qualified}
for (a, b) in edge_weight:
    degree[a] += 1
    degree[b] += 1

# ── Community detection (label propagation) ────────────────────────────────────
import random, collections

community = {aid: i for i, aid in enumerate(sorted(qualified))}

# Adjacency
adj = {aid: [] for aid in qualified}
for (a, b) in edge_weight:
    adj[a].append(b)
    adj[b].append(a)

random.seed(42)
for iteration in range(30):
    order = list(qualified)
    random.shuffle(order)
    changed = False
    for aid in order:
        nbrs = adj[aid]
        if not nbrs: continue
        freq = collections.Counter(community[nb] for nb in nbrs)
        best = freq.most_common(1)[0][0]
        if best != community[aid]:
            community[aid] = best
            changed = True
    if not changed:
        break

# Relabel: largest community = 0
comm_sizes = collections.Counter(community.values())
remap = {c: i for i, (c, _) in enumerate(comm_sizes.most_common())}
for aid in community:
    community[aid] = remap[community[aid]]

n_communities = len(set(community.values()))
print(f"Communities detected: {n_communities}")

# ── Colors ─────────────────────────────────────────────────────────────────────
PALETTE = [
    "#4ECDC4","#74B9FF","#A29BFE","#FFE66D",
    "#FF6B6B","#FD79A8","#00CEC9","#FDCB6E",
    "#6C5CE7","#55EFC4"
]

# ── Assign integer IDs (sorted by n_papers desc) ──────────────────────────────
sorted_aids = sorted(qualified, key=lambda aid: len(author_papers[aid]), reverse=True)
idx_map = {aid: i for i, aid in enumerate(sorted_aids)}

# ── Build nodes ────────────────────────────────────────────────────────────────
def get_papers(aid):
    papers = []
    for clave in list(author_papers[aid])[:5]:
        meta = paper_meta.get(clave, {
            "clave": clave, "anio": None,
            "titulo": clave[:55], "url": ""
        })
        papers.append(meta)
    return papers

nodes_out = []
for aid in sorted_aids:
    comm  = community[aid]
    color = PALETTE[comm % len(PALETTE)]
    nodes_out.append({
        "id":       idx_map[aid],
        "autor_id": aid,
        "nombre":   author_name[aid],
        "n_papers": len(author_papers[aid]),
        "grado":    degree[aid],
        "community": comm,
        "color":    color,
        "papers":   get_papers(aid)
    })

# ── Build links ────────────────────────────────────────────────────────────────
links_out = [
    {"source": idx_map[a], "target": idx_map[b], "value": w}
    for (a, b), w in edge_weight.items()
]

# ── Max degree author ──────────────────────────────────────────────────────────
max_deg_aid = max(degree, key=degree.get)
max_deg_name = author_name[max_deg_aid]
max_deg_val  = degree[max_deg_aid]
print(f"Most connected author: {max_deg_name} (degree {max_deg_val})")

# ── Write JSON ─────────────────────────────────────────────────────────────────
OUT_DIR.mkdir(parents=True, exist_ok=True)

output = {
    "meta": {
        "n_nodes": len(nodes_out),
        "n_links": len(links_out),
        "n_communities": n_communities,
        "color_method": "label_propagation",
        "max_degree_author": max_deg_name,
        "max_degree": max_deg_val
    },
    "nodes": nodes_out,
    "links": links_out
}

with open(OUT_JSON, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

size_kb = OUT_JSON.stat().st_size / 1024
print(f"\nSaved: {OUT_JSON}")
print(f"Size:  {size_kb:.1f} KB")
print(f"Nodes: {len(nodes_out)}, Links: {len(links_out)}")
print("\nDone. Now open docs/charts/red_coautoria.html in your browser.")
