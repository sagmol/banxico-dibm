"""
04_red_coautoria.py
===================
Construye y analiza la red de coautoría del corpus DIBM.

Un nodo = un autor. Una arista = al menos un paper coescrito.
El peso de la arista = número de papers coescritos.

Genera en docs/charts/:
  - red_coautoria.html          Red interactiva (Plotly)
  - autores_top_productivos.html  Ranking de autores más prolíficos
  - autores_centralidad.html    Autores más centrales en la red

Genera en data/processed/:
  - autores_metricas.csv        Métricas de red por autor
  - red_aristas.csv             Todas las aristas de la red
"""

import pandas as pd
import networkx as nx
import plotly.graph_objects as go
import plotly.express as px
from itertools import combinations
from pathlib import Path
import math

BASE   = Path(__file__).resolve().parent.parent
PROC   = BASE / "data" / "processed"
CHARTS = BASE / "docs" / "charts"
CHARTS.mkdir(parents=True, exist_ok=True)

# ── Carga ──────────────────────────────────────────────────────────────────────
papers = pd.read_csv(PROC / "papers.csv")
pa     = pd.read_csv(PROC / "paper_authors.csv")
authors = pd.read_csv(PROC / "authors.csv")

papers = papers[papers["anio"].notna()].copy()
papers["anio"] = papers["anio"].astype(int)

# Unir autores con papers
pa_full = pa.merge(papers[["clave","anio","status"]], left_on="clave_paper", right_on="clave", how="inner")
pa_full = pa_full[pa_full["status"] == "Publicado"]

# Nombre de display por autor
autor_nombre = authors.set_index("id")["presentacion"].to_dict()

# ── Producción por autor ────────────────────────────────────────────────────────
prod = pa_full.groupby("autor_id")["clave_paper"].nunique().reset_index()
prod.columns = ["autor_id","n_papers"]
prod["nombre"] = prod["autor_id"].map(autor_nombre).fillna("Desconocido")
prod = prod.sort_values("n_papers", ascending=False)

# ══════════════════════════════════════════════════════════════════════════════
# 1. RANKING DE AUTORES MÁS PROLÍFICOS
# ══════════════════════════════════════════════════════════════════════════════
top30 = prod.head(30).sort_values("n_papers")

fig1 = go.Figure(go.Bar(
    x=top30["n_papers"], y=top30["nombre"],
    orientation="h",
    marker_color="#023047",
    text=top30["n_papers"], textposition="outside",
    hovertemplate="<b>%{y}</b><br>%{x} documentos<extra></extra>",
))
fig1.update_layout(
    title=dict(
        text="Autores más prolíficos del DIBM<br>"
             "<sup>Top 30 por número de documentos publicados</sup>",
        font_size=18,
    ),
    xaxis_title="Número de documentos",
    plot_bgcolor="white", paper_bgcolor="white",
    font_family="Georgia, serif",
    showlegend=False, height=700,
    margin=dict(l=200),
)
fig1.update_xaxes(showgrid=True, gridcolor="#eeeeee")
fig1.write_html(CHARTS / "autores_top_productivos.html", include_plotlyjs="cdn")
print("✓ autores_top_productivos.html")


# ══════════════════════════════════════════════════════════════════════════════
# 2. CONSTRUIR RED DE COAUTORÍA
# ══════════════════════════════════════════════════════════════════════════════
G = nx.Graph()

# Añadir nodos (todos los autores)
for _, row in prod.iterrows():
    G.add_node(row["autor_id"], nombre=row["nombre"], n_papers=int(row["n_papers"]))

# Añadir aristas (pares de coautores en el mismo paper)
aristas_data = []
papers_multi = pa_full.groupby("clave_paper")["autor_id"].apply(list)

for clave, autores_lista in papers_multi.items():
    autores_lista = list(set(autores_lista))  # deduplicar
    if len(autores_lista) < 2:
        continue
    for a, b in combinations(sorted(autores_lista), 2):
        if G.has_edge(a, b):
            G[a][b]["weight"] += 1
        else:
            G.add_edge(a, b, weight=1)
            aristas_data.append({"autor_a": a, "autor_b": b, "peso": 1})

# Actualizar pesos en aristas_data
aristas_df = pd.DataFrame([
    {
        "autor_a": u,
        "nombre_a": G.nodes[u].get("nombre",""),
        "autor_b": v,
        "nombre_b": G.nodes[v].get("nombre",""),
        "peso": G[u][v]["weight"],
    }
    for u, v in G.edges()
])
aristas_df.to_csv(PROC / "red_aristas.csv", index=False, encoding="utf-8")
print(f"✓ red_aristas.csv ({len(aristas_df)} aristas)")

print(f"Red: {G.number_of_nodes()} nodos, {G.number_of_edges()} aristas")


# ══════════════════════════════════════════════════════════════════════════════
# 3. MÉTRICAS DE RED
# ══════════════════════════════════════════════════════════════════════════════
# Componente gigante
gcc = max(nx.connected_components(G), key=len)
G_gcc = G.subgraph(gcc).copy()
print(f"Componente gigante: {G_gcc.number_of_nodes()} nodos ({G_gcc.number_of_nodes()/G.number_of_nodes()*100:.1f}%)")

# Centralidades (solo en componente gigante para betweenness)
degree_cent    = nx.degree_centrality(G)
between_cent   = nx.betweenness_centrality(G_gcc, weight="weight", normalized=True)
# Extender betweenness a todos los nodos
between_all    = {n: between_cent.get(n, 0.0) for n in G.nodes()}

metricas = []
for node in G.nodes():
    metricas.append({
        "autor_id":           node,
        "nombre":             G.nodes[node].get("nombre",""),
        "n_papers":           G.nodes[node].get("n_papers", 0),
        "grado":              G.degree(node),
        "grado_ponderado":    sum(d["weight"] for _, _, d in G.edges(node, data=True)),
        "centralidad_grado":  round(degree_cent[node], 4),
        "centralidad_entre":  round(between_all[node], 6),
        "en_gcc":             node in gcc,
    })

metricas_df = pd.DataFrame(metricas).sort_values("n_papers", ascending=False)
metricas_df.to_csv(PROC / "autores_metricas.csv", index=False, encoding="utf-8")
print("✓ autores_metricas.csv")


# ══════════════════════════════════════════════════════════════════════════════
# 4. TOP AUTORES POR CENTRALIDAD (betweenness)
# ══════════════════════════════════════════════════════════════════════════════
top_entre = metricas_df.nlargest(25, "centralidad_entre").sort_values("centralidad_entre")

fig_entre = go.Figure(go.Bar(
    x=top_entre["centralidad_entre"],
    y=top_entre["nombre"],
    orientation="h",
    marker_color="#219ebc",
    text=top_entre["n_papers"].astype(str) + " docs",
    textposition="outside",
    customdata=top_entre[["n_papers","grado"]].values,
    hovertemplate="<b>%{y}</b><br>Centralidad: %{x:.4f}<br>Papers: %{customdata[0]}<br>Coautores directos: %{customdata[1]}<extra></extra>",
))
fig_entre.update_layout(
    title=dict(
        text="Autores más centrales en la red de coautoría<br>"
             "<sup>Centralidad de intermediación (betweenness) — quién conecta clusters</sup>",
        font_size=18,
    ),
    xaxis_title="Centralidad de intermediación",
    plot_bgcolor="white", paper_bgcolor="white",
    font_family="Georgia, serif",
    showlegend=False, height=620,
    margin=dict(l=200),
)
fig_entre.update_xaxes(showgrid=True, gridcolor="#eeeeee")
fig_entre.write_html(CHARTS / "autores_centralidad.html", include_plotlyjs="cdn")
print("✓ autores_centralidad.html")


# ══════════════════════════════════════════════════════════════════════════════
# 5. RED INTERACTIVA (componente gigante, top nodos)
# ══════════════════════════════════════════════════════════════════════════════
# Para la visualización usamos solo autores con ≥ 2 papers (más legible)
nodos_vis = {n for n in G_gcc.nodes() if G_gcc.nodes[n].get("n_papers", 0) >= 2}
G_vis = G_gcc.subgraph(nodos_vis).copy()

print(f"Subgrafo visualización: {G_vis.number_of_nodes()} nodos, {G_vis.number_of_edges()} aristas")

# Layout con spring
pos = nx.spring_layout(G_vis, weight="weight", seed=42, k=1.5/math.sqrt(G_vis.number_of_nodes()))

# Detectar comunidades
communities = nx.community.louvain_communities(G_vis, weight="weight", seed=42)
node_community = {}
for i, comm in enumerate(communities):
    for node in comm:
        node_community[node] = i

PALETTE = [
    "#023047","#219ebc","#ffb703","#fb8500","#e63946",
    "#2a9d8f","#e9c46a","#264653","#a8dadc","#457b9d",
    "#f4a261","#6d6875","#b5838d","#e76f51","#588157",
]

# Aristas
edge_traces = []
for u, v, data in G_vis.edges(data=True):
    x0, y0 = pos[u]
    x1, y1 = pos[v]
    w = data.get("weight", 1)
    edge_traces.append(go.Scatter(
        x=[x0, x1, None], y=[y0, y1, None],
        mode="lines",
        line=dict(width=min(w * 0.8, 4), color="rgba(150,150,150,0.35)"),
        hoverinfo="none",
        showlegend=False,
    ))

# Nodos
node_x = [pos[n][0] for n in G_vis.nodes()]
node_y = [pos[n][1] for n in G_vis.nodes()]
node_text = [G_vis.nodes[n].get("nombre","") for n in G_vis.nodes()]
node_papers = [G_vis.nodes[n].get("n_papers", 1) for n in G_vis.nodes()]
node_degree = [G_vis.degree(n) for n in G_vis.nodes()]
node_colors = [PALETTE[node_community.get(n, 0) % len(PALETTE)] for n in G_vis.nodes()]
node_sizes = [6 + min(p * 2.5, 30) for p in node_papers]

node_trace = go.Scatter(
    x=node_x, y=node_y,
    mode="markers+text",
    marker=dict(
        size=node_sizes,
        color=node_colors,
        line=dict(width=0.8, color="white"),
        opacity=0.9,
    ),
    text=[n if p >= 5 else "" for n, p in zip(node_text, node_papers)],
    textposition="top center",
    textfont=dict(size=8, family="Georgia, serif"),
    customdata=list(zip(node_text, node_papers, node_degree)),
    hovertemplate="<b>%{customdata[0]}</b><br>Papers: %{customdata[1]}<br>Coautores directos: %{customdata[2]}<extra></extra>",
    showlegend=False,
)

fig_red = go.Figure(data=edge_traces + [node_trace])
fig_red.update_layout(
    title=dict(
        text="Red de coautoría — Banco de México (DIBM)<br>"
             "<sup>Autores con ≥ 2 publicaciones · colores = comunidades (Louvain) · tamaño = productividad</sup>",
        font_size=16,
    ),
    plot_bgcolor="#fafafa", paper_bgcolor="white",
    font_family="Georgia, serif",
    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
    height=700,
    margin=dict(l=20, r=20, t=80, b=20),
    hovermode="closest",
)
fig_red.write_html(CHARTS / "red_coautoria.html", include_plotlyjs="cdn")
print("✓ red_coautoria.html")


# ── Resumen en consola ─────────────────────────────────────────────────────────
print()
print("══════════════════════════════════════════════")
print("  MÉTRICAS DE LA RED")
print("══════════════════════════════════════════════")
print(f"  Nodos totales:           {G.number_of_nodes()}")
print(f"  Aristas totales:         {G.number_of_edges()}")
print(f"  Componente gigante:      {G_gcc.number_of_nodes()} nodos ({G_gcc.number_of_nodes()/G.number_of_nodes()*100:.0f}%)")
print(f"  Comunidades detectadas:  {len(communities)}")
print(f"  Densidad (gcc):          {nx.density(G_gcc):.4f}")
print()
print("  TOP 10 MÁS PROLÍFICOS:")
for _, r in prod.head(10).iterrows():
    print(f"    {r['nombre']:<30} {int(r['n_papers']):>3} papers")
print("══════════════════════════════════════════════")
