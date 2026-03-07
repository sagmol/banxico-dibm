"""
02_analisis_temporal.py
=======================
Analiza la distribución temporal del corpus DIBM (1978-2025).

Genera visualizaciones interactivas (Plotly HTML) guardadas en docs/charts/:
  - temporal_produccion_anual.html     Documentos por año con hitos históricos
  - temporal_produccion_decada.html    Documentos por década
  - temporal_acumulado.html            Producción acumulada
  - temporal_autores_activos.html      Autores activos por año
  - temporal_jel_grupos.html           Evolución de grupos JEL en el tiempo

También guarda un CSV resumen en data/processed/resumen_temporal.csv
"""

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from pathlib import Path
import sys

# ── Rutas ──────────────────────────────────────────────────────────────────────
BASE    = Path(__file__).resolve().parent.parent
PROC    = BASE / "data" / "processed"
CHARTS  = BASE / "docs" / "charts"
CHARTS.mkdir(parents=True, exist_ok=True)

# ── Carga ──────────────────────────────────────────────────────────────────────
papers  = pd.read_csv(PROC / "papers.csv")
pa      = pd.read_csv(PROC / "paper_authors.csv")
pj      = pd.read_csv(PROC / "paper_jel.csv")

# Solo documentos con año válido y publicados
papers = papers[papers["anio"].notna()].copy()
papers["anio"] = papers["anio"].astype(int)
papers_pub = papers[papers["status"] == "Publicado"].copy()

print(f"Total con año: {len(papers)} | Publicados: {len(papers_pub)}")
print(f"Rango: {papers['anio'].min()} – {papers['anio'].max()}")

# ── Hitos históricos ───────────────────────────────────────────────────────────
HITOS = [
    (1995, "Crisis del Peso"),
    (1999, "Primera meta de inflación"),
    (2001, "Régimen IT formal"),
    (2008, "Crisis financiera global"),
    (2020, "COVID-19"),
]

COLORES = {
    "pre_crisis":   "#8ecae6",   # 1978-1994
    "transicion":   "#219ebc",   # 1995-2001
    "it_maduro":    "#023047",   # 2002-2019
    "reciente":     "#ffb703",   # 2020+
}

def color_periodo(anio):
    if anio < 1995:   return COLORES["pre_crisis"]
    if anio <= 2001:  return COLORES["transicion"]
    if anio <= 2019:  return COLORES["it_maduro"]
    return COLORES["reciente"]

# ══════════════════════════════════════════════════════════════════════════════
# 1. PRODUCCIÓN ANUAL
# ══════════════════════════════════════════════════════════════════════════════
por_anio = papers_pub.groupby("anio").size().reset_index(name="n_docs")
# Rellenar años sin documentos
anio_range = range(papers_pub["anio"].min(), papers_pub["anio"].max() + 1)
por_anio = por_anio.set_index("anio").reindex(anio_range, fill_value=0).reset_index()
por_anio.columns = ["anio", "n_docs"]
por_anio["color"] = por_anio["anio"].apply(color_periodo)

fig = go.Figure()

# Barras coloreadas por período
for periodo, color, label in [
    ("pre_crisis",  COLORES["pre_crisis"],  "Pre-estabilización (1978–1994)"),
    ("transicion",  COLORES["transicion"],  "Transición (1995–2001)"),
    ("it_maduro",   COLORES["it_maduro"],   "IT consolidado (2002–2019)"),
    ("reciente",    COLORES["reciente"],    "Reciente (2020–2025)"),
]:
    mask = por_anio["color"] == color
    fig.add_trace(go.Bar(
        x=por_anio[mask]["anio"],
        y=por_anio[mask]["n_docs"],
        name=label,
        marker_color=color,
        hovertemplate="<b>%{x}</b><br>%{y} documentos<extra></extra>",
    ))

# Líneas de hitos
for anio, nombre in HITOS:
    fig.add_vline(
        x=anio, line_dash="dot", line_color="#e63946", line_width=1.5,
        annotation_text=nombre,
        annotation_position="top",
        annotation_font_size=10,
        annotation_font_color="#e63946",
    )

fig.update_layout(
    title=dict(
        text="Producción anual de documentos de investigación<br>"
             "<sup>Banco de México (DIBM) · 1978–2025</sup>",
        font_size=18,
    ),
    xaxis_title="Año",
    yaxis_title="Número de documentos",
    barmode="stack",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    plot_bgcolor="white",
    paper_bgcolor="white",
    font_family="Georgia, serif",
    hovermode="x unified",
    height=500,
)
fig.update_xaxes(showgrid=False)
fig.update_yaxes(showgrid=True, gridcolor="#eeeeee")

out = CHARTS / "temporal_produccion_anual.html"
fig.write_html(out, include_plotlyjs="cdn")
print(f"✓ {out.name}")


# ══════════════════════════════════════════════════════════════════════════════
# 2. PRODUCCIÓN POR DÉCADA
# ══════════════════════════════════════════════════════════════════════════════
por_decada = papers_pub.groupby("decada").size().reset_index(name="n_docs")
por_decada["decada"] = por_decada["decada"].astype(int)
por_decada["label"] = por_decada["decada"].astype(str) + "s"

fig2 = px.bar(
    por_decada, x="label", y="n_docs",
    color="n_docs",
    color_continuous_scale=["#8ecae6", "#023047"],
    labels={"label": "Década", "n_docs": "Documentos"},
    text="n_docs",
)
fig2.update_traces(textposition="outside")
fig2.update_layout(
    title=dict(
        text="Producción por década<br>"
             "<sup>Banco de México (DIBM)</sup>",
        font_size=18,
    ),
    coloraxis_showscale=False,
    plot_bgcolor="white",
    paper_bgcolor="white",
    font_family="Georgia, serif",
    height=420,
)
fig2.update_yaxes(showgrid=True, gridcolor="#eeeeee")

out2 = CHARTS / "temporal_produccion_decada.html"
fig2.write_html(out2, include_plotlyjs="cdn")
print(f"✓ {out2.name}")


# ══════════════════════════════════════════════════════════════════════════════
# 3. PRODUCCIÓN ACUMULADA
# ══════════════════════════════════════════════════════════════════════════════
por_anio_sorted = por_anio.sort_values("anio").copy()
por_anio_sorted["acumulado"] = por_anio_sorted["n_docs"].cumsum()

fig3 = go.Figure()
fig3.add_trace(go.Scatter(
    x=por_anio_sorted["anio"],
    y=por_anio_sorted["acumulado"],
    mode="lines",
    fill="tozeroy",
    line=dict(color="#023047", width=2),
    fillcolor="rgba(2, 48, 71, 0.15)",
    hovertemplate="<b>%{x}</b><br>Acumulado: %{y} documentos<extra></extra>",
    name="Producción acumulada",
))

for anio, nombre in HITOS:
    acum = por_anio_sorted[por_anio_sorted["anio"] == anio]["acumulado"].values
    if len(acum):
        fig3.add_annotation(
            x=anio, y=acum[0],
            text=nombre, showarrow=True,
            arrowhead=2, arrowcolor="#e63946",
            font=dict(size=9, color="#e63946"),
            ax=30, ay=-30,
        )

fig3.update_layout(
    title=dict(
        text="Crecimiento acumulado del corpus<br>"
             "<sup>Banco de México (DIBM) · 1978–2025</sup>",
        font_size=18,
    ),
    xaxis_title="Año",
    yaxis_title="Documentos acumulados",
    plot_bgcolor="white",
    paper_bgcolor="white",
    font_family="Georgia, serif",
    showlegend=False,
    height=460,
)
fig3.update_xaxes(showgrid=False)
fig3.update_yaxes(showgrid=True, gridcolor="#eeeeee")

out3 = CHARTS / "temporal_acumulado.html"
fig3.write_html(out3, include_plotlyjs="cdn")
print(f"✓ {out3.name}")


# ══════════════════════════════════════════════════════════════════════════════
# 4. AUTORES ACTIVOS POR AÑO
# ══════════════════════════════════════════════════════════════════════════════
# Unir paper_authors con año del paper
pa_anio = pa.merge(
    papers_pub[["clave", "anio"]],
    left_on="clave_paper", right_on="clave", how="inner"
)
autores_por_anio = (
    pa_anio.groupby("anio")["autor_id"].nunique()
    .reset_index(name="autores_activos")
)

fig4 = go.Figure()
fig4.add_trace(go.Scatter(
    x=autores_por_anio["anio"],
    y=autores_por_anio["autores_activos"],
    mode="lines+markers",
    line=dict(color="#219ebc", width=2),
    marker=dict(size=5),
    hovertemplate="<b>%{x}</b><br>Autores activos: %{y}<extra></extra>",
))

for anio, nombre in HITOS:
    fig4.add_vline(
        x=anio, line_dash="dot", line_color="#e63946", line_width=1,
    )

fig4.update_layout(
    title=dict(
        text="Autores activos por año<br>"
             "<sup>Número de investigadores con al menos un documento publicado</sup>",
        font_size=18,
    ),
    xaxis_title="Año",
    yaxis_title="Autores activos",
    plot_bgcolor="white",
    paper_bgcolor="white",
    font_family="Georgia, serif",
    showlegend=False,
    height=420,
)
fig4.update_xaxes(showgrid=False)
fig4.update_yaxes(showgrid=True, gridcolor="#eeeeee")

out4 = CHARTS / "temporal_autores_activos.html"
fig4.write_html(out4, include_plotlyjs="cdn")
print(f"✓ {out4.name}")


# ══════════════════════════════════════════════════════════════════════════════
# 5. EVOLUCIÓN DE GRUPOS JEL EN EL TIEMPO
# ══════════════════════════════════════════════════════════════════════════════
# Grupos JEL: primera letra del código
pj_anio = pj.merge(
    papers_pub[["clave", "anio"]],
    left_on="clave_paper", right_on="clave", how="inner"
)
pj_anio["grupo_jel"] = pj_anio["jel_code"].str[0]

# Nombres de grupos JEL relevantes
JEL_NOMBRES = {
    "C": "C — Métodos cuantitativos",
    "E": "E — Macroeconomía / Política monetaria",
    "F": "F — Economía internacional",
    "G": "G — Economía financiera",
    "H": "H — Economía pública",
    "J": "J — Economía laboral",
    "L": "L — Organización industrial",
    "O": "O — Desarrollo económico",
    "Q": "Q — Economía ambiental",
}

# Solo períodos con suficientes datos: desde 1995
pj_anio = pj_anio[pj_anio["anio"] >= 1995]

top_grupos = pj_anio["grupo_jel"].value_counts().head(8).index.tolist()
pj_top = pj_anio[pj_anio["grupo_jel"].isin(top_grupos)]

jel_evol = (
    pj_top.groupby(["anio", "grupo_jel"])
    .size()
    .reset_index(name="n")
)

# Normalizar como % del total de asignaciones JEL por año
total_por_anio = pj_anio.groupby("anio").size().reset_index(name="total")
jel_evol = jel_evol.merge(total_por_anio, on="anio")
jel_evol["pct"] = (jel_evol["n"] / jel_evol["total"] * 100).round(1)
jel_evol["grupo_label"] = jel_evol["grupo_jel"].map(JEL_NOMBRES).fillna(jel_evol["grupo_jel"])

fig5 = px.area(
    jel_evol, x="anio", y="pct", color="grupo_label",
    labels={"anio": "Año", "pct": "% de asignaciones JEL", "grupo_label": "Grupo JEL"},
    color_discrete_sequence=px.colors.qualitative.Set2,
)
fig5.update_layout(
    title=dict(
        text="Distribución de grupos JEL en el tiempo<br>"
             "<sup>% de asignaciones por año · corpus DIBM desde 1995</sup>",
        font_size=18,
    ),
    plot_bgcolor="white",
    paper_bgcolor="white",
    font_family="Georgia, serif",
    legend=dict(orientation="h", yanchor="bottom", y=-0.4, xanchor="left", x=0),
    height=520,
    hovermode="x unified",
)
fig5.update_xaxes(showgrid=False)
fig5.update_yaxes(showgrid=True, gridcolor="#eeeeee")

for anio, nombre in HITOS:
    if anio >= 1995:
        fig5.add_vline(
            x=anio, line_dash="dot", line_color="#333", line_width=1,
            annotation_text=nombre, annotation_position="top left",
            annotation_font_size=9,
        )

out5 = CHARTS / "temporal_jel_grupos.html"
fig5.write_html(out5, include_plotlyjs="cdn")
print(f"✓ {out5.name}")


# ══════════════════════════════════════════════════════════════════════════════
# 6. CSV RESUMEN TEMPORAL
# ══════════════════════════════════════════════════════════════════════════════
resumen = por_anio.copy()
resumen = resumen.merge(autores_por_anio, on="anio", how="left")

def periodo(anio):
    if anio < 1995:   return "Pre-estabilización"
    if anio <= 2001:  return "Transición"
    if anio <= 2019:  return "IT consolidado"
    return "Reciente"

resumen["periodo"] = resumen["anio"].apply(periodo)
resumen.to_csv(PROC / "resumen_temporal.csv", index=False, encoding="utf-8")
print(f"✓ resumen_temporal.csv")

# ── Resumen en consola ─────────────────────────────────────────────────────────
print()
print("══════════════════════════════════════════════")
print("  PRODUCCIÓN POR PERÍODO")
print("══════════════════════════════════════════════")
for p in ["Pre-estabilización", "Transición", "IT consolidado", "Reciente"]:
    n = resumen[resumen["periodo"] == p]["n_docs"].sum()
    años = resumen[resumen["periodo"] == p]["anio"]
    print(f"  {p:<25} {n:>4} docs  ({años.min()}–{años.max()})")
print("══════════════════════════════════════════════")
print(f"\nCharts guardados en: {CHARTS}")
