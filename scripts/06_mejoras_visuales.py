"""
06_mejoras_visuales.py
======================
Re-genera las visualizaciones principales con mejoras de diseño
basadas en las filosofías de Tufte, Lupi y Cairo.

Cambios por autor:
  TUFTE:  - Gridlines apenas visibles o eliminadas
          - Etiquetas directas en lugar de leyendas flotantes
          - Escalas consistentes en small multiples
          - Sin bordes de ejes innecesarios

  LUPI:   - Anotaciones narrativas en puntos clave (el "por qué")
          - Hover enriquecido con contexto humano
          - Etiquetas de clusters directamente en el gráfico

  CAIRO:  - Advertencia explícita de t-SNE (ejes sin significado)
          - Escala X unificada en jel_top_por_periodo (error antes)
          - Barras siempre desde 0
          - Subtítulo = hallazgo, no descripción

Gráficos actualizados (sobreescriben los anteriores):
  temporal_produccion_anual.html
  jel_top_por_periodo.html
  clusters_scatter.html
  clusters_palabras.html
  red_coautoria.html  (etiquetas en nodos principales)
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import networkx as nx
from itertools import combinations
import math
from pathlib import Path

BASE   = Path(__file__).resolve().parent.parent
PROC   = BASE / "data" / "processed"
CHARTS = BASE / "docs" / "charts"

# ── Estilo base Tufte ──────────────────────────────────────────────────────────
FONT   = "Georgia, serif"
WHITE  = "white"
GRID   = "rgba(0,0,0,0.06)"   # gridline casi invisible
AZ_OSC = "#023047"
AZ_MED = "#219ebc"
AZ_CLA = "#8ecae6"
AMARI  = "#ffb703"
ROJO   = "#e63946"

def base_layout(**kwargs):
    """Layout base Tufte: sin chartjunk."""
    defaults = dict(
        font_family=FONT,
        plot_bgcolor=WHITE,
        paper_bgcolor=WHITE,
        showlegend=False,
        margin=dict(t=80, b=40, l=60, r=40),
    )
    defaults.update(kwargs)
    return defaults

def clean_xaxis(**kwargs):
    return dict(showgrid=False, zeroline=False, showline=False,
                tickfont_size=11, **kwargs)

def clean_yaxis(**kwargs):
    defaults = dict(showgrid=True, gridcolor=GRID, zeroline=False,
                    showline=False, tickfont_size=11)
    defaults.update(kwargs)
    return defaults

# ── Carga de datos ─────────────────────────────────────────────────────────────
papers   = pd.read_csv(PROC / "papers.csv")
pa       = pd.read_csv(PROC / "paper_authors.csv")
pj       = pd.read_csv(PROC / "paper_jel.csv")
authors  = pd.read_csv(PROC / "authors.csv")
topicos  = pd.read_csv(PROC / "papers_topicos.csv")

papers = papers[papers["anio"].notna()].copy()
papers["anio"] = papers["anio"].astype(int)
papers_pub = papers[papers["status"] == "Publicado"].copy()

def periodo(anio):
    if anio < 1995:   return "Pre-estabilización\n(1978–1994)"
    if anio <= 2001:  return "Transición\n(1995–2001)"
    if anio <= 2019:  return "IT consolidado\n(2002–2019)"
    return "Reciente\n(2020–2025)"

COLORES_PERIODO = {
    "Pre-estabilización\n(1978–1994)": AZ_CLA,
    "Transición\n(1995–2001)":         AZ_MED,
    "IT consolidado\n(2002–2019)":     AZ_OSC,
    "Reciente\n(2020–2025)":           AMARI,
}

# ══════════════════════════════════════════════════════════════════════════════
# 1. PRODUCCIÓN ANUAL — Tufte + Lupi
#    Tufte: etiquetas de período directas, sin leyenda, grid mínimo
#    Lupi: anotaciones narrativas en hitos ("qué pasó aquí y por qué importa")
# ══════════════════════════════════════════════════════════════════════════════
por_anio = papers_pub.groupby("anio").size().reset_index(name="n_docs")
anio_range = range(papers_pub["anio"].min(), papers_pub["anio"].max() + 1)
por_anio = por_anio.set_index("anio").reindex(anio_range, fill_value=0).reset_index()
por_anio.columns = ["anio","n_docs"]
por_anio["periodo"] = por_anio["anio"].apply(periodo)
por_anio["color"] = por_anio["periodo"].map(COLORES_PERIODO)

fig1 = go.Figure()

# Una traza por período (Tufte: colores semánticos, sin leyenda)
for per, col in COLORES_PERIODO.items():
    sub = por_anio[por_anio["periodo"] == per]
    fig1.add_trace(go.Bar(
        x=sub["anio"], y=sub["n_docs"],
        marker_color=col,
        marker_line_width=0,
        hovertemplate="<b>%{x}</b> · %{y} documentos<extra></extra>",
        showlegend=False,
    ))

# Tufte: etiquetas de período directamente en el gráfico (sin caja de leyenda)
LABEL_PERIODOS = [
    (1986, 3.5,  "Pre-\nestabilización", AZ_CLA),
    (1998, 9.5,  "Transición", AZ_MED),
    (2010, 22.5, "IT consolidado", AZ_OSC),
    (2022, 22.5, "Reciente", "#c8890a"),
]
for x, y, txt, col in LABEL_PERIODOS:
    fig1.add_annotation(
        x=x, y=y, text=f"<b>{txt}</b>",
        font=dict(size=9, color=col, family=FONT),
        showarrow=False, bgcolor="rgba(255,255,255,0.7)",
        borderpad=2,
    )

# Lupi: anotaciones narrativas — el "por qué" de los quiebres
NARRATIVAS = [
    (1995, 9,  "Crisis del Peso (1994–95):<br>primeros años del DIBM moderno",  "right"),
    (2001, 15, "Adopción formal del<br>esquema de metas de inflación",          "right"),
    (2008, 18, "Crisis financiera global:<br>pico de investigación sobre riesgo","left"),
    (2020, 20, "COVID-19: expansión hacia<br>bienestar y mercado laboral",       "left"),
]
for anio, y_ann, texto, side in NARRATIVAS:
    ax_offset = 60 if side == "right" else -60
    fig1.add_annotation(
        x=anio, y=por_anio[por_anio["anio"]==anio]["n_docs"].values[0] + 0.5,
        text=texto,
        font=dict(size=8.5, color="#444", family=FONT),
        showarrow=True, arrowhead=2, arrowcolor=ROJO, arrowwidth=1.2,
        arrowsize=0.8, ax=ax_offset, ay=-45,
        bgcolor="rgba(255,255,255,0.85)", bordercolor=ROJO,
        borderwidth=1, borderpad=4,
    )

fig1.update_layout(
    **base_layout(height=520),
    title=dict(
        text="La producción de investigación se triplicó tras las metas de inflación<br>"
             "<sup style='color:#666'>Documentos publicados por año · Banco de México (DIBM) · 1978–2025</sup>",
        font_size=17, x=0,
    ),
    xaxis=dict(**clean_xaxis(title="")),
    yaxis=dict(**clean_yaxis(title="Documentos publicados")),
    bargap=0.1,
)
fig1.write_html(CHARTS / "temporal_produccion_anual.html", include_plotlyjs="cdn")
print("✓ temporal_produccion_anual.html")


# ══════════════════════════════════════════════════════════════════════════════
# 2. JEL TOP POR PERÍODO — Cairo: escala X unificada (FIX CRÍTICO)
#    El gráfico anterior tenía escalas diferentes por panel → mentira visual
#    Cairo: "si la escala cambia por panel, la comparación es imposible"
# ══════════════════════════════════════════════════════════════════════════════
pj_full = pj.merge(papers_pub[["clave","anio"]], left_on="clave_paper", right_on="clave", how="inner")
pj_full["periodo"] = pj_full["anio"].apply(periodo)

ORDEN_PERIODOS = [
    "Pre-estabilización\n(1978–1994)",
    "Transición\n(1995–2001)",
    "IT consolidado\n(2002–2019)",
    "Reciente\n(2020–2025)",
]
periodos_en_datos = [p for p in ORDEN_PERIODOS if p in pj_full["periodo"].unique()]

COLOR_MAP = {
    "E": AZ_OSC, "C": AZ_MED, "F": AZ_CLA,
    "G": AMARI,  "H": "#fb8500", "J": "#a8dadc",
    "O": "#457b9d", "D": ROJO,
}

# Cairo: calcular máximo global ANTES de graficar
global_max = 0
top5_por_periodo = {}
for per in periodos_en_datos:
    sub = pj_full[pj_full["periodo"] == per]["jel_code"].value_counts().head(5)
    top5_por_periodo[per] = sub
    if len(sub): global_max = max(global_max, sub.max())
global_max_plot = global_max * 1.15   # margen para etiquetas

fig2 = make_subplots(
    rows=1, cols=len(periodos_en_datos),
    subplot_titles=[p.replace("\n"," ") for p in periodos_en_datos],
    shared_xaxes=False,
    horizontal_spacing=0.08,
)

for i, per in enumerate(periodos_en_datos, 1):
    sub = top5_por_periodo[per]
    colors = [COLOR_MAP.get(c[0], "#adb5bd") for c in sub.index]
    fig2.add_trace(go.Bar(
        x=sub.values, y=sub.index,
        orientation="h",
        marker_color=colors,
        marker_line_width=0,
        text=sub.values, textposition="outside",
        textfont_size=10,
        hovertemplate="<b>%{y}</b><br>%{x} asignaciones en este período<extra></extra>",
        showlegend=False,
    ), row=1, col=i)
    # Cairo: misma escala en todos los paneles
    fig2.update_xaxes(range=[0, global_max_plot], row=1, col=i,
                      showgrid=False, zeroline=False, showline=False,
                      tickfont_size=10)
    fig2.update_yaxes(autorange="reversed", row=1, col=i,
                      showgrid=False, zeroline=False, showline=False,
                      tickfont_size=10)

fig2.update_layout(
    **base_layout(height=360),
    title=dict(
        text="E31 (inflación) domina en todos los períodos excepto en el reciente<br>"
             "<sup style='color:#666'>Top 5 códigos JEL por período · escala X unificada para comparación válida</sup>",
        font_size=16, x=0,
    ),
)
fig2.write_html(CHARTS / "jel_top_por_periodo.html", include_plotlyjs="cdn")
print("✓ jel_top_por_periodo.html  [FIX: escala X unificada]")


# ══════════════════════════════════════════════════════════════════════════════
# 3. CLUSTERS SCATTER (t-SNE) — Cairo + Lupi
#    Cairo: advertencia explícita de limitaciones del t-SNE
#    Lupi:  etiquetas de cluster directamente en el mapa (sin leyenda separada)
#    Tufte: eliminar la leyenda flotante
# ══════════════════════════════════════════════════════════════════════════════
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import NMF
from sklearn.manifold import TSNE
from sklearn.preprocessing import normalize
from nltk.corpus import stopwords
import re

# Re-usar datos de tópicos ya calculados
topicos["anio"] = topicos["anio"].astype(int)

TOPIC_LABELS = {
    0: "Deuda y riesgo financiero",
    1: "Tipo de cambio e inflación",
    2: "Mercado laboral",
    3: "Métodos y pronósticos",
    4: "Economía regional y manufactura",
    5: "Precios y competencia",
    6: "Política monetaria",
    7: "Tipo de cambio (pass-through)",
    8: "Tasas y curva de rendimientos",
    9: "Transferencias y bienestar",
}
N_TOPICS = 10
TOPIC_COLORS = (px.colors.qualitative.Set2 + px.colors.qualitative.Pastel1)[:N_TOPICS]

# Re-ejecutar t-SNE sobre los scores de tópicos
score_cols = [c for c in topicos.columns if c.startswith("score_t")]
W = topicos[score_cols].values
X_norm = normalize(W)
tsne = TSNE(n_components=2, random_state=42, perplexity=35,
            learning_rate="auto", init="pca", n_iter=1000)
coords = tsne.fit_transform(X_norm)
topicos["tsne_x"] = coords[:, 0]
topicos["tsne_y"] = coords[:, 1]

# Calcular centroide de cada cluster (para etiquetas Lupi/Tufte)
centroides = topicos.groupby("topic_id")[["tsne_x","tsne_y"]].mean()

fig3 = go.Figure()

for i in range(N_TOPICS):
    sub = topicos[topicos["topic_id"] == i]
    titulo_col = "titulo_ing" if "titulo_ing" in sub.columns else "titulo_esp"
    hover_txt = (
        "<b>" + sub[titulo_col].fillna(sub.get("titulo_esp","")).fillna("").str[:65] + "…</b><br>" +
        "Año: " + sub["anio"].astype(str) + "<br>" +
        "<i>" + TOPIC_LABELS.get(i,"") + "</i>"
    )
    fig3.add_trace(go.Scatter(
        x=sub["tsne_x"], y=sub["tsne_y"],
        mode="markers",
        marker=dict(
            size=8, color=TOPIC_COLORS[i], opacity=0.72,
            line=dict(width=0.5, color="white"),
        ),
        text=hover_txt,
        hovertemplate="%{text}<extra></extra>",
        showlegend=False,
    ))

# Lupi + Tufte: etiquetas directas en centroides (sin leyenda separada)
for i, row in centroides.iterrows():
    label = TOPIC_LABELS.get(i, "")
    # Abreviar para no saturar
    short = label if len(label) <= 22 else label[:20] + "…"
    fig3.add_annotation(
        x=row["tsne_x"], y=row["tsne_y"],
        text=f"<b>{short}</b>",
        font=dict(size=8.5, color=TOPIC_COLORS[i], family=FONT),
        showarrow=False,
        bgcolor="rgba(255,255,255,0.82)",
        borderpad=2,
    )

# Cairo: advertencia sobre t-SNE en el subtítulo
fig3.update_layout(
    **base_layout(height=640, margin=dict(t=90, b=30, l=30, r=30)),
    title=dict(
        text="Mapa temático del corpus DIBM · Banco de México<br>"
             "<sup style='color:#888'>Proyección t-SNE sobre scores NMF · Los ejes no tienen unidades interpretables · "
             "La proximidad refleja similitud temática local, no distancias globales</sup>",
        font_size=15, x=0,
    ),
    xaxis=dict(**clean_xaxis(title="", showticklabels=False)),
    yaxis=dict(**clean_yaxis(title="", showticklabels=False, showgrid=False)),
)
fig3.write_html(CHARTS / "clusters_scatter.html", include_plotlyjs="cdn")
print("✓ clusters_scatter.html  [Cairo: advertencia t-SNE + Tufte: etiquetas directas]")


# ══════════════════════════════════════════════════════════════════════════════
# 4. PALABRAS CLAVE POR TÓPICO — Cairo: escala X unificada en small multiples
# ══════════════════════════════════════════════════════════════════════════════

# Necesitamos re-calcular H (NMF components) para tener las palabras
stop_en = set(stopwords.words("english"))
stop_es = set(stopwords.words("spanish"))
DOMAIN_STOPS = {
    "model","models","paper","study","results","result","using","use","used",
    "also","show","shows","shown","find","finds","found","suggest","suggests",
    "evidence","data","estimate","estimates","estimated","effect","effects",
    "analysis","analyze","analyses","approach","based","two","one","three",
    "however","well","may","can","although","within","across","among",
    "mexico","mexican","banco","banxico","central","bank",
    "artículo","documento","este","esta","mediante","través","embargo",
    "así","tanto","sido","pueden","puede",
}
STOPWORDS = stop_en | stop_es | DOMAIN_STOPS

papers_text = papers.copy()
papers_text["texto"] = papers_text["resumen_ing"].fillna("")
mask = papers_text["resumen_ing"].isna() | (papers_text["resumen_ing"].str.strip()=="")
papers_text.loc[mask,"texto"] = papers_text.loc[mask,"resumen_esp"].fillna("")
papers_text = papers_text[papers_text["texto"].str.split().str.len().fillna(0)>=30]

def preprocess(text):
    text = text.lower()
    text = re.sub(r"[^a-záéíóúüñ\s]"," ",text)
    tokens = [t for t in text.split() if len(t)>3 and t not in STOPWORDS]
    return " ".join(tokens)

papers_text["texto_proc"] = papers_text["texto"].apply(preprocess)

tfidf = TfidfVectorizer(ngram_range=(1,2), max_df=0.80, min_df=3,
                        max_features=4000, sublinear_tf=True)
X = tfidf.fit_transform(papers_text["texto_proc"])
vocab = tfidf.get_feature_names_out()
nmf  = NMF(n_components=N_TOPICS, random_state=42, max_iter=400, init="nndsvda")
nmf.fit(X)
H = nmf.components_

def top_words(idx, n=8):
    return [vocab[i] for i in H[idx].argsort()[::-1][:n]]

# Cairo: calcular máximo global para unified scale
global_word_max = max(
    H[i][H[i].argsort()[::-1][:8]].max() for i in range(N_TOPICS)
)

fig4 = make_subplots(
    rows=2, cols=5,
    subplot_titles=[f"<b>{TOPIC_LABELS.get(i,'')}</b>" for i in range(N_TOPICS)],
    vertical_spacing=0.20, horizontal_spacing=0.06,
)
for i in range(N_TOPICS):
    r = i // 5 + 1
    c = i % 5 + 1
    words  = top_words(i, 8)
    scores = sorted(H[i][H[i].argsort()[::-1][:8]], reverse=True)
    fig4.add_trace(go.Bar(
        x=scores, y=words,
        orientation="h",
        marker_color=TOPIC_COLORS[i],
        marker_line_width=0,
        showlegend=False,
        hovertemplate="%{y}: %{x:.3f}<extra></extra>",
    ), row=r, col=c)
    fig4.update_yaxes(autorange="reversed", showgrid=False,
                      zeroline=False, showline=False,
                      tickfont_size=9, row=r, col=c)
    # Cairo: misma escala X en todos los paneles
    fig4.update_xaxes(range=[0, global_word_max * 1.1],
                      showgrid=False, zeroline=False, showline=False,
                      tickfont_size=8, showticklabels=False,
                      row=r, col=c)

fig4.update_layout(
    **base_layout(height=600),
    title=dict(
        text="Vocabulario característico de cada tópico (NMF)<br>"
             "<sup style='color:#888'>Escala X unificada · permite comparar peso relativo entre tópicos</sup>",
        font_size=15, x=0,
    ),
)
fig4.write_html(CHARTS / "clusters_palabras.html", include_plotlyjs="cdn")
print("✓ clusters_palabras.html  [Cairo: escala X unificada]")


# ══════════════════════════════════════════════════════════════════════════════
# 5. RED DE COAUTORÍA — Lupi: nombres visibles de nodos principales
#    Tufte: eliminar nodos aislados del subgrafo, reducir ruido visual
# ══════════════════════════════════════════════════════════════════════════════
pa_full = pa.merge(papers_pub[["clave","anio","status"]],
                   left_on="clave_paper", right_on="clave", how="inner")
prod = pa_full.groupby("autor_id")["clave_paper"].nunique().reset_index()
prod.columns = ["autor_id","n_papers"]
autor_nombre = authors.set_index("id")["presentacion"].to_dict()
prod["nombre"] = prod["autor_id"].map(autor_nombre).fillna("")

G = nx.Graph()
for _, r in prod.iterrows():
    G.add_node(r["autor_id"], nombre=r["nombre"], n_papers=int(r["n_papers"]))

papers_multi = pa_full.groupby("clave_paper")["autor_id"].apply(list)
for clave, alist in papers_multi.items():
    alist = list(set(alist))
    if len(alist) < 2: continue
    for a, b in combinations(sorted(alist), 2):
        if G.has_edge(a, b): G[a][b]["weight"] += 1
        else: G.add_edge(a, b, weight=1)

gcc = max(nx.connected_components(G), key=len)
G_gcc = G.subgraph(gcc).copy()

# Tufte: solo autores con ≥ 2 papers para reducir ruido
nodos_vis = {n for n in G_gcc.nodes() if G_gcc.nodes[n].get("n_papers",0) >= 2}
G_vis = G_gcc.subgraph(nodos_vis).copy()

# Lupi: identificar top 8 por grado (los que merecen etiqueta)
degree_dict = dict(G_vis.degree())
top_nodos = sorted(degree_dict, key=degree_dict.get, reverse=True)[:8]

communities = nx.community.louvain_communities(G_vis, weight="weight", seed=42)
node_community = {}
for idx, comm in enumerate(communities):
    for node in comm: node_community[node] = idx

PALETTE = [
    AZ_OSC, AZ_MED, AMARI, "#fb8500", ROJO,
    "#2a9d8f", "#e9c46a", "#264653", "#a8dadc", "#457b9d",
]
pos = nx.spring_layout(G_vis, weight="weight", seed=42,
                       k=1.5/math.sqrt(G_vis.number_of_nodes()))

# Aristas (Tufte: muy tenues)
edge_traces = []
for u, v, data in G_vis.edges(data=True):
    x0,y0 = pos[u]; x1,y1 = pos[v]
    w = data.get("weight",1)
    edge_traces.append(go.Scatter(
        x=[x0,x1,None], y=[y0,y1,None], mode="lines",
        line=dict(width=min(w*0.6,3), color="rgba(160,160,160,0.25)"),
        hoverinfo="none", showlegend=False,
    ))

# Nodos
node_x = [pos[n][0] for n in G_vis.nodes()]
node_y = [pos[n][1] for n in G_vis.nodes()]
node_nombres = [G_vis.nodes[n].get("nombre","") for n in G_vis.nodes()]
node_papers  = [G_vis.nodes[n].get("n_papers",1) for n in G_vis.nodes()]
node_degree  = [G_vis.degree(n) for n in G_vis.nodes()]
node_colors  = [PALETTE[node_community.get(n,0) % len(PALETTE)] for n in G_vis.nodes()]
node_sizes   = [5 + min(p*2.2,28) for p in node_papers]

hover_red = [
    f"<b>{nom}</b><br>{pap} documentos · {deg} coautores directos"
    for nom, pap, deg in zip(node_nombres, node_papers, node_degree)
]

node_trace = go.Scatter(
    x=node_x, y=node_y, mode="markers",
    marker=dict(size=node_sizes, color=node_colors, opacity=0.88,
                line=dict(width=0.6, color="white")),
    text=hover_red,
    hovertemplate="%{text}<extra></extra>",
    showlegend=False,
)

fig5 = go.Figure(data=edge_traces + [node_trace])

# Lupi: etiquetas visibles para los más conectados
nodos_list = list(G_vis.nodes())
for n in top_nodos:
    if n not in pos: continue
    x, y = pos[n]
    nombre = G_vis.nodes[n].get("nombre","")
    n_pap  = G_vis.nodes[n].get("n_papers",0)
    # Apellido solamente para no saturar
    apellido = nombre.split()[-1] if nombre else ""
    fig5.add_annotation(
        x=x, y=y,
        text=f"<b>{apellido}</b>",
        font=dict(size=8, color="#222", family=FONT),
        showarrow=False, yshift=10,
        bgcolor="rgba(255,255,255,0.75)", borderpad=2,
    )

fig5.update_layout(
    **base_layout(height=680, plot_bgcolor="#fafafa",
                  margin=dict(t=85, b=20, l=20, r=20)),
    title=dict(
        text="Red de coautoría · Banco de México (DIBM)<br>"
             "<sup style='color:#888'>Autores con ≥ 2 publicaciones · color = comunidad (Louvain) · "
             "tamaño = productividad · etiquetas = 8 más conectados</sup>",
        font_size=15, x=0,
    ),
    xaxis=dict(**clean_xaxis(showticklabels=False, title="")),
    yaxis=dict(**clean_yaxis(showticklabels=False, title="", showgrid=False)),
    hovermode="closest",
)
fig5.write_html(CHARTS / "red_coautoria.html", include_plotlyjs="cdn")
print("✓ red_coautoria.html  [Lupi: etiquetas top 8 + Tufte: aristas más tenues]")

print("\nTodos los gráficos actualizados.")
