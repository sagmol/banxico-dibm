"""
05_clusters_tematicos.py
========================
Análisis de clusters temáticos del corpus DIBM mediante NLP.

Estrategia:
  - Texto: abstracts en inglés (75% cobertura); fallback a español
  - Vectorización: TF-IDF con bigramas, filtros de frecuencia
  - Modelo: NMF (Non-negative Matrix Factorization) — 10 tópicos
  - Proyección 2D: t-SNE para visualización de dispersión
  - Asignación: cada documento se asigna al tópico dominante

Genera en docs/charts/:
  - clusters_scatter.html         Mapa 2D de documentos por tópico
  - clusters_palabras.html        Top palabras por tópico
  - clusters_distribucion.html    Cuántos docs por tópico
  - clusters_evolucion.html       Tópicos en el tiempo
  - clusters_calor_periodo.html   Heatmap tópico × período

Genera en data/processed/:
  - papers_topicos.csv            Cada doc con su tópico asignado + scores
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import NMF
from sklearn.manifold import TSNE
from sklearn.preprocessing import normalize
from nltk.corpus import stopwords
from nltk.stem import SnowballStemmer
import re
from pathlib import Path

BASE   = Path(__file__).resolve().parent.parent
PROC   = BASE / "data" / "processed"
CHARTS = BASE / "docs" / "charts"

# ── Parámetros ─────────────────────────────────────────────────────────────────
N_TOPICS  = 10
N_WORDS   = 12    # palabras clave por tópico para mostrar
TSNE_SEED = 42
NMF_SEED  = 42

# ── Carga ──────────────────────────────────────────────────────────────────────
papers = pd.read_csv(PROC / "papers.csv")
papers = papers[papers["anio"].notna()].copy()
papers["anio"] = papers["anio"].astype(int)

# Texto: inglés preferido, fallback español
papers["texto"] = papers["resumen_ing"].fillna("")
papers["idioma_usado"] = "inglés"
mask_sin_ing = papers["resumen_ing"].isna() | (papers["resumen_ing"].str.strip() == "")
papers.loc[mask_sin_ing, "texto"] = papers.loc[mask_sin_ing, "resumen_esp"].fillna("")
papers.loc[mask_sin_ing, "idioma_usado"] = "español"

# Solo documentos con texto suficiente (>= 30 palabras)
papers["n_palabras"] = papers["texto"].str.split().str.len().fillna(0)
papers_ok = papers[papers["n_palabras"] >= 30].copy()

print(f"Docs con texto suficiente: {len(papers_ok)} / {len(papers)}")
print(f"  En inglés:  {(papers_ok['idioma_usado']=='inglés').sum()}")
print(f"  En español: {(papers_ok['idioma_usado']=='español').sum()}")

# ── Preprocesamiento de texto ──────────────────────────────────────────────────
stop_en = set(stopwords.words("english"))
stop_es = set(stopwords.words("spanish"))
STOPWORDS = stop_en | stop_es

# Stopwords adicionales específicas del dominio (muy frecuentes pero no informativas)
DOMAIN_STOPS = {
    "model", "models", "paper", "paper's", "study", "results", "result",
    "using", "use", "used", "also", "show", "shows", "shown", "find",
    "finds", "found", "suggest", "suggests", "evidence", "data", "estimate",
    "estimates", "estimated", "effect", "effects", "analysis", "analyze",
    "analyses", "approach", "based", "two", "one", "three", "however",
    "well", "may", "can", "although", "within", "across", "among",
    "mexico", "mexican", "banco", "banxico", "central", "bank",
    "artículo", "documento", "este", "esta", "mediante", "través",
    "embargo", "así", "tanto", "sido", "sido", "pueden", "puede",
}
STOPWORDS |= DOMAIN_STOPS

stemmer_en = SnowballStemmer("english")

def preprocess(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-záéíóúüñ\s]", " ", text)
    tokens = text.split()
    tokens = [t for t in tokens if len(t) > 3 and t not in STOPWORDS]
    return " ".join(tokens)

papers_ok["texto_proc"] = papers_ok["texto"].apply(preprocess)

# ── TF-IDF ────────────────────────────────────────────────────────────────────
tfidf = TfidfVectorizer(
    ngram_range=(1, 2),
    max_df=0.80,     # ignora términos en >80% de docs
    min_df=3,        # ignora términos en <3 docs
    max_features=4000,
    sublinear_tf=True,
)
X = tfidf.fit_transform(papers_ok["texto_proc"])
vocab = tfidf.get_feature_names_out()
print(f"Vocabulario TF-IDF: {len(vocab)} términos")

# ── NMF ───────────────────────────────────────────────────────────────────────
nmf = NMF(n_components=N_TOPICS, random_state=NMF_SEED, max_iter=400, init="nndsvda")
W = nmf.fit_transform(X)   # docs × tópicos
H = nmf.components_        # tópicos × palabras

# Tópico dominante por documento
topic_dominant = np.argmax(W, axis=1)
topic_score    = W[np.arange(len(W)), topic_dominant]

# Top palabras por tópico
def top_words(topic_idx, n=N_WORDS):
    return [vocab[i] for i in H[topic_idx].argsort()[::-1][:n]]

# Etiquetas manuales inferidas de las palabras clave (revisar y ajustar si es necesario)
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

# Mostrar tópicos para verificar
print("\n══════════════════════════════════════════════")
print("  TÓPICOS DETECTADOS (NMF)")
print("══════════════════════════════════════════════")
for i in range(N_TOPICS):
    words = ", ".join(top_words(i, 8))
    print(f"  T{i:02d} {TOPIC_LABELS.get(i,'?'):<30} {words}")
print("══════════════════════════════════════════════\n")

# Agregar tópicos al dataframe
papers_ok = papers_ok.copy()
papers_ok["topic_id"]    = topic_dominant
papers_ok["topic_label"] = papers_ok["topic_id"].map(TOPIC_LABELS)
papers_ok["topic_score"] = topic_score.round(4)

# Scores completos de todos los tópicos
for i in range(N_TOPICS):
    papers_ok[f"score_t{i:02d}"] = W[:, i].round(4)

papers_ok.to_csv(PROC / "papers_topicos.csv", index=False, encoding="utf-8")
print("✓ papers_topicos.csv")

# Períodos
def periodo(anio):
    if anio < 1995:   return "Pre-estabilización\n(1978–1994)"
    if anio <= 2001:  return "Transición\n(1995–2001)"
    if anio <= 2019:  return "IT consolidado\n(2002–2019)"
    return "Reciente\n(2020–2025)"

ORDEN_PERIODOS = [
    "Pre-estabilización\n(1978–1994)",
    "Transición\n(1995–2001)",
    "IT consolidado\n(2002–2019)",
    "Reciente\n(2020–2025)",
]

papers_ok["periodo"] = papers_ok["anio"].apply(periodo)

# Paleta de colores por tópico
TOPIC_COLORS = (px.colors.qualitative.Set2 + px.colors.qualitative.Pastel1)[:N_TOPICS]

# ══════════════════════════════════════════════════════════════════════════════
# 1. PALABRAS CLAVE POR TÓPICO
# ══════════════════════════════════════════════════════════════════════════════
fig1 = make_subplots(
    rows=2, cols=5,
    subplot_titles=[f"T{i}: {TOPIC_LABELS.get(i,'')}" for i in range(N_TOPICS)],
    vertical_spacing=0.18, horizontal_spacing=0.06,
)

for i in range(N_TOPICS):
    r = i // 5 + 1
    c = i % 5 + 1
    words = top_words(i, 8)
    scores = sorted(H[i][H[i].argsort()[::-1][:8]], reverse=True)
    fig1.add_trace(go.Bar(
        x=scores, y=words,
        orientation="h",
        marker_color=TOPIC_COLORS[i],
        showlegend=False,
        hovertemplate="%{y}: %{x:.3f}<extra></extra>",
    ), row=r, col=c)
    fig1.update_yaxes(autorange="reversed", row=r, col=c)

fig1.update_layout(
    title=dict(
        text="Palabras clave por tópico (NMF)<br>"
             "<sup>Corpus DIBM · Banco de México · abstracts</sup>",
        font_size=16,
    ),
    plot_bgcolor="white", paper_bgcolor="white",
    font_family="Georgia, serif",
    height=620,
)
fig1.write_html(CHARTS / "clusters_palabras.html", include_plotlyjs="cdn")
print("✓ clusters_palabras.html")


# ══════════════════════════════════════════════════════════════════════════════
# 2. DISTRIBUCIÓN DE DOCUMENTOS POR TÓPICO
# ══════════════════════════════════════════════════════════════════════════════
dist = papers_ok.groupby(["topic_id","topic_label"]).size().reset_index(name="n")
dist = dist.sort_values("n", ascending=True)
dist["color"] = dist["topic_id"].map(lambda i: TOPIC_COLORS[i])

fig2 = go.Figure(go.Bar(
    x=dist["n"], y=dist["topic_label"],
    orientation="h",
    marker_color=dist["color"],
    text=dist["n"], textposition="outside",
    hovertemplate="<b>%{y}</b><br>%{x} documentos<extra></extra>",
))
fig2.update_layout(
    title=dict(
        text="Documentos por tópico<br>"
             "<sup>Tópico dominante asignado por NMF</sup>",
        font_size=18,
    ),
    xaxis_title="Número de documentos",
    plot_bgcolor="white", paper_bgcolor="white",
    font_family="Georgia, serif",
    showlegend=False, height=440,
    margin=dict(l=220),
)
fig2.update_xaxes(showgrid=True, gridcolor="#eeeeee")
fig2.write_html(CHARTS / "clusters_distribucion.html", include_plotlyjs="cdn")
print("✓ clusters_distribucion.html")


# ══════════════════════════════════════════════════════════════════════════════
# 3. EVOLUCIÓN DE TÓPICOS EN EL TIEMPO (desde 1995)
# ══════════════════════════════════════════════════════════════════════════════
evol = papers_ok[papers_ok["anio"] >= 1995].groupby(["anio","topic_label"]).size().reset_index(name="n")

# Normalizar como % por año
total_año = evol.groupby("anio")["n"].transform("sum")
evol["pct"] = (evol["n"] / total_año * 100).round(1)

fig3 = px.area(
    evol, x="anio", y="pct", color="topic_label",
    color_discrete_sequence=TOPIC_COLORS,
    labels={"anio":"Año","pct":"% de documentos","topic_label":"Tópico"},
)
fig3.add_vline(x=2001, line_dash="dot", line_color="#333", line_width=1.5,
               annotation_text="IT formal (2001)", annotation_font_size=9)
fig3.add_vline(x=2008, line_dash="dot", line_color="#333", line_width=1,
               annotation_text="Crisis 2008", annotation_font_size=9,
               annotation_position="top left")
fig3.update_layout(
    title=dict(
        text="Evolución de tópicos en el tiempo<br>"
             "<sup>% de documentos por tópico dominante · desde 1995</sup>",
        font_size=18,
    ),
    plot_bgcolor="white", paper_bgcolor="white",
    font_family="Georgia, serif",
    legend=dict(orientation="h", yanchor="bottom", y=-0.45, xanchor="left", x=0),
    height=520, hovermode="x unified",
)
fig3.update_xaxes(showgrid=False)
fig3.update_yaxes(showgrid=True, gridcolor="#eeeeee")
fig3.write_html(CHARTS / "clusters_evolucion.html", include_plotlyjs="cdn")
print("✓ clusters_evolucion.html")


# ══════════════════════════════════════════════════════════════════════════════
# 4. HEATMAP TÓPICO × PERÍODO
# ══════════════════════════════════════════════════════════════════════════════
hm = papers_ok.groupby(["periodo","topic_label"]).size().reset_index(name="n")
total_p = hm.groupby("periodo")["n"].transform("sum")
hm["pct"] = (hm["n"] / total_p * 100).round(1)

pivot = hm.pivot(index="topic_label", columns="periodo", values="pct").fillna(0)
pivot = pivot.reindex(columns=[p for p in ORDEN_PERIODOS if p in pivot.columns])
pivot["total"] = pivot.sum(axis=1)
pivot = pivot.sort_values("total", ascending=False).drop(columns="total")

fig4 = go.Figure(go.Heatmap(
    z=pivot.values,
    x=[c.replace("\n"," ") for c in pivot.columns],
    y=pivot.index,
    colorscale=[[0,"#f8f9fa"],[0.3,"#8ecae6"],[0.65,"#219ebc"],[1,"#023047"]],
    text=[[f"{v:.0f}%" for v in row] for row in pivot.values],
    texttemplate="%{text}",
    hovertemplate="<b>%{y}</b><br>%{x}<br>%{z:.1f}%<extra></extra>",
))
fig4.update_layout(
    title=dict(
        text="Distribución temática por período histórico<br>"
             "<sup>% de documentos con ese tópico dominante en cada período</sup>",
        font_size=18,
    ),
    plot_bgcolor="white", paper_bgcolor="white",
    font_family="Georgia, serif",
    height=480, margin=dict(l=230),
    xaxis=dict(side="top"),
)
fig4.write_html(CHARTS / "clusters_calor_periodo.html", include_plotlyjs="cdn")
print("✓ clusters_calor_periodo.html")


# ══════════════════════════════════════════════════════════════════════════════
# 5. SCATTER 2D (t-SNE)
# ══════════════════════════════════════════════════════════════════════════════
print("Calculando t-SNE (puede tardar ~30 seg)...")
X_norm = normalize(W)   # normalizar scores NMF
tsne = TSNE(n_components=2, random_state=TSNE_SEED, perplexity=35,
            learning_rate="auto", init="pca", n_iter=1000)
coords = tsne.fit_transform(X_norm)

papers_ok = papers_ok.copy()
papers_ok["tsne_x"] = coords[:, 0]
papers_ok["tsne_y"] = coords[:, 1]

# Hover text
papers_ok["hover"] = (
    "<b>" + papers_ok["titulo_ing"].fillna(papers_ok["titulo_esp"]).fillna("").str[:70] + "...</b><br>" +
    "Año: " + papers_ok["anio"].astype(str) + "<br>" +
    "Tópico: " + papers_ok["topic_label"].fillna("")
)

fig5 = go.Figure()
for i in range(N_TOPICS):
    sub = papers_ok[papers_ok["topic_id"] == i]
    fig5.add_trace(go.Scatter(
        x=sub["tsne_x"], y=sub["tsne_y"],
        mode="markers",
        name=f"T{i}: {TOPIC_LABELS.get(i,'')}",
        marker=dict(
            size=7 + sub["anio"].apply(lambda a: max(0, (a-1990)/5)),
            color=TOPIC_COLORS[i],
            opacity=0.75,
            line=dict(width=0.5, color="white"),
        ),
        text=sub["hover"],
        hovertemplate="%{text}<extra></extra>",
    ))

fig5.update_layout(
    title=dict(
        text="Mapa temático del corpus DIBM (t-SNE)<br>"
             "<sup>Cada punto = un documento · color = tópico dominante · tamaño ≈ año de publicación</sup>",
        font_size=16,
    ),
    plot_bgcolor="#fafafa", paper_bgcolor="white",
    font_family="Georgia, serif",
    legend=dict(orientation="v", x=1.01, y=1, font_size=10),
    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
    height=640,
    hovermode="closest",
)
fig5.write_html(CHARTS / "clusters_scatter.html", include_plotlyjs="cdn")
print("✓ clusters_scatter.html")


# ── Resumen final ──────────────────────────────────────────────────────────────
print()
print("══════════════════════════════════════════════")
print("  DISTRIBUCIÓN POR TÓPICO")
print("══════════════════════════════════════════════")
for i in range(N_TOPICS):
    n = (papers_ok["topic_id"] == i).sum()
    label = TOPIC_LABELS.get(i, "?")
    words = ", ".join(top_words(i, 4))
    print(f"  T{i:02d} {label:<32} {n:>3} docs  [{words}]")
print("══════════════════════════════════════════════")
