"""
03_analisis_jel.py
==================
Analiza la distribución temática del corpus DIBM usando códigos JEL.

Genera en docs/charts/:
  - jel_top20.html              Top 20 códigos JEL más frecuentes
  - jel_grupos_barras.html      Frecuencia por grupo JEL (letra)
  - jel_heatmap_periodo.html    Heatmap: grupo JEL × período histórico
  - jel_top_por_periodo.html    Top 5 JEL por período (subplots)
  - jel_e_detalle.html          Detalle del grupo E (macro/política monetaria)
"""

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from pathlib import Path

BASE   = Path(__file__).resolve().parent.parent
PROC   = BASE / "data" / "processed"
CHARTS = BASE / "docs" / "charts"
CHARTS.mkdir(parents=True, exist_ok=True)

# ── Carga ──────────────────────────────────────────────────────────────────────
papers = pd.read_csv(PROC / "papers.csv")
pj     = pd.read_csv(PROC / "paper_jel.csv")
jel_cat = pd.read_csv(PROC / "jel_codes.csv")

papers = papers[papers["anio"].notna()].copy()
papers["anio"] = papers["anio"].astype(int)

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

papers["periodo"] = papers["anio"].apply(periodo)

# Unir JEL con papers
pj_full = pj.merge(papers[["clave","anio","periodo"]], left_on="clave_paper", right_on="clave", how="inner")
pj_full["grupo"] = pj_full["jel_code"].str[0]

# Nombres de grupos JEL
JEL_GRUPOS = {
    "A": "A — General",
    "B": "B — Historia del pensamiento",
    "C": "C — Métodos cuantitativos",
    "D": "D — Microeconomía",
    "E": "E — Macroeconomía / Política monetaria",
    "F": "F — Economía internacional",
    "G": "G — Economía financiera",
    "H": "H — Economía pública",
    "I": "I — Salud / Educación / Bienestar",
    "J": "J — Economía laboral",
    "K": "K — Derecho y economía",
    "L": "L — Organización industrial",
    "M": "M — Administración de empresas",
    "N": "N — Historia económica",
    "O": "O — Desarrollo y crecimiento",
    "P": "P — Sistemas económicos",
    "Q": "Q — Economía ambiental",
    "R": "R — Economía urbana / Regional",
}

# ══════════════════════════════════════════════════════════════════════════════
# 1. TOP 20 CÓDIGOS JEL
# ══════════════════════════════════════════════════════════════════════════════
top20 = pj_full["jel_code"].value_counts().head(20).reset_index()
top20.columns = ["jel_code","n"]
top20["grupo"] = top20["jel_code"].str[0]
top20["grupo_label"] = top20["grupo"].map(JEL_GRUPOS).fillna(top20["grupo"])

COLOR_MAP = {
    "E": "#023047", "C": "#219ebc", "F": "#8ecae6",
    "G": "#ffb703", "H": "#fb8500", "J": "#a8dadc",
    "O": "#457b9d", "D": "#e63946",
}
top20["color"] = top20["grupo"].map(COLOR_MAP).fillna("#adb5bd")

fig1 = go.Figure(go.Bar(
    x=top20["n"], y=top20["jel_code"],
    orientation="h",
    marker_color=top20["color"],
    customdata=top20["grupo_label"],
    hovertemplate="<b>%{y}</b><br>%{customdata}<br>%{x} asignaciones<extra></extra>",
    text=top20["n"], textposition="outside",
))
fig1.update_layout(
    title=dict(
        text="Top 20 códigos JEL más frecuentes<br>"
             "<sup>Corpus DIBM · Banco de México · total de asignaciones</sup>",
        font_size=18,
    ),
    xaxis_title="Número de asignaciones",
    yaxis=dict(autorange="reversed"),
    plot_bgcolor="white", paper_bgcolor="white",
    font_family="Georgia, serif",
    showlegend=False, height=560,
)
fig1.update_xaxes(showgrid=True, gridcolor="#eeeeee")
fig1.write_html(CHARTS / "jel_top20.html", include_plotlyjs="cdn")
print("✓ jel_top20.html")


# ══════════════════════════════════════════════════════════════════════════════
# 2. FRECUENCIA POR GRUPO JEL
# ══════════════════════════════════════════════════════════════════════════════
grupos = pj_full["grupo"].value_counts().reset_index()
grupos.columns = ["grupo","n"]
grupos["label"] = grupos["grupo"].map(JEL_GRUPOS).fillna(grupos["grupo"])
grupos["color"] = grupos["grupo"].map(COLOR_MAP).fillna("#adb5bd")
grupos = grupos.sort_values("n", ascending=True)

fig2 = go.Figure(go.Bar(
    x=grupos["n"], y=grupos["label"],
    orientation="h",
    marker_color=grupos["color"],
    text=grupos["n"], textposition="outside",
    hovertemplate="<b>%{y}</b><br>%{x} asignaciones<extra></extra>",
))
fig2.update_layout(
    title=dict(
        text="Frecuencia por grupo JEL<br>"
             "<sup>Corpus DIBM · Banco de México</sup>",
        font_size=18,
    ),
    xaxis_title="Asignaciones totales",
    plot_bgcolor="white", paper_bgcolor="white",
    font_family="Georgia, serif",
    showlegend=False, height=500,
    margin=dict(l=260),
)
fig2.update_xaxes(showgrid=True, gridcolor="#eeeeee")
fig2.write_html(CHARTS / "jel_grupos_barras.html", include_plotlyjs="cdn")
print("✓ jel_grupos_barras.html")


# ══════════════════════════════════════════════════════════════════════════════
# 3. HEATMAP: GRUPO JEL × PERÍODO
# ══════════════════════════════════════════════════════════════════════════════
hm = pj_full.groupby(["periodo","grupo"]).size().reset_index(name="n")

# Normalizar por total de asignaciones en cada período
total_periodo = hm.groupby("periodo")["n"].transform("sum")
hm["pct"] = (hm["n"] / total_periodo * 100).round(1)

# Pivot
pivot = hm.pivot(index="grupo", columns="periodo", values="pct").fillna(0)
pivot = pivot.reindex(columns=[p for p in ORDEN_PERIODOS if p in pivot.columns])
pivot["total"] = pivot.sum(axis=1)
pivot = pivot.sort_values("total", ascending=False).drop(columns="total")
pivot.index = pivot.index.map(lambda g: JEL_GRUPOS.get(g, g))

fig3 = go.Figure(go.Heatmap(
    z=pivot.values,
    x=[p.replace("\n", " ") for p in pivot.columns],
    y=pivot.index,
    colorscale=[[0,"#f8f9fa"],[0.3,"#8ecae6"],[0.6,"#219ebc"],[1,"#023047"]],
    text=[[f"{v:.1f}%" for v in row] for row in pivot.values],
    texttemplate="%{text}",
    hovertemplate="<b>%{y}</b><br>%{x}<br>%{z:.1f}% de asignaciones<extra></extra>",
))
fig3.update_layout(
    title=dict(
        text="Distribución temática por período histórico<br>"
             "<sup>% de asignaciones JEL dentro de cada período</sup>",
        font_size=18,
    ),
    plot_bgcolor="white", paper_bgcolor="white",
    font_family="Georgia, serif",
    height=540,
    margin=dict(l=280),
    xaxis=dict(side="top"),
)
fig3.write_html(CHARTS / "jel_heatmap_periodo.html", include_plotlyjs="cdn")
print("✓ jel_heatmap_periodo.html")


# ══════════════════════════════════════════════════════════════════════════════
# 4. TOP 5 JEL POR PERÍODO (subplots)
# ══════════════════════════════════════════════════════════════════════════════
periodos_ordenados = [p for p in ORDEN_PERIODOS if p in pj_full["periodo"].unique()]
fig4 = make_subplots(
    rows=1, cols=len(periodos_ordenados),
    subplot_titles=[p.replace("\n", " ") for p in periodos_ordenados],
    shared_yaxes=False,
)

for i, per in enumerate(periodos_ordenados, 1):
    sub = pj_full[pj_full["periodo"] == per]["jel_code"].value_counts().head(5)
    colors = [COLOR_MAP.get(c[0], "#adb5bd") for c in sub.index]
    fig4.add_trace(go.Bar(
        x=sub.values, y=sub.index,
        orientation="h",
        marker_color=colors,
        text=sub.values, textposition="outside",
        hovertemplate="<b>%{y}</b><br>%{x} asignaciones<extra></extra>",
        showlegend=False,
    ), row=1, col=i)
    fig4.update_yaxes(autorange="reversed", row=1, col=i)

fig4.update_layout(
    title=dict(
        text="Top 5 códigos JEL por período histórico<br>"
             "<sup>Banco de México · corpus DIBM</sup>",
        font_size=18,
    ),
    plot_bgcolor="white", paper_bgcolor="white",
    font_family="Georgia, serif",
    height=380,
)
fig4.write_html(CHARTS / "jel_top_por_periodo.html", include_plotlyjs="cdn")
print("✓ jel_top_por_periodo.html")


# ══════════════════════════════════════════════════════════════════════════════
# 5. DETALLE GRUPO E (MACRO / POLÍTICA MONETARIA)
# ══════════════════════════════════════════════════════════════════════════════
E_SUBCATS = {
    "E0": "E0 — General",
    "E1": "E1 — Modelos macroeconómicos",
    "E2": "E2 — Consumo, ahorro, producción",
    "E3": "E3 — Precios, inflación, ciclos de negocio",
    "E4": "E4 — Dinero y tasas de interés",
    "E5": "E5 — Política monetaria",
    "E6": "E6 — Política macroeconómica",
    "E7": "E7 — Macro y finanzas",
}

pj_E = pj_full[pj_full["grupo"] == "E"].copy()
pj_E["subcat"] = pj_E["jel_code"].str[:2]
pj_E["subcat_label"] = pj_E["subcat"].map(E_SUBCATS).fillna(pj_E["subcat"])

# Evolución de subcategorías E desde 1995
pj_E_evol = pj_E[pj_E["anio"] >= 1995].groupby(["anio","subcat_label"]).size().reset_index(name="n")

fig5 = px.area(
    pj_E_evol, x="anio", y="n", color="subcat_label",
    labels={"anio":"Año","n":"Asignaciones","subcat_label":"Subcategoría"},
    color_discrete_sequence=px.colors.sequential.Blues_r[:len(E_SUBCATS)],
)
fig5.update_layout(
    title=dict(
        text="Grupo E: Macroeconomía y política monetaria — evolución interna<br>"
             "<sup>Número de asignaciones por subcategoría JEL · desde 1995</sup>",
        font_size=18,
    ),
    plot_bgcolor="white", paper_bgcolor="white",
    font_family="Georgia, serif",
    legend=dict(orientation="h", yanchor="bottom", y=-0.4, xanchor="left", x=0),
    height=500, hovermode="x unified",
)
fig5.update_xaxes(showgrid=False)
fig5.update_yaxes(showgrid=True, gridcolor="#eeeeee")

# Hito IT 2001
fig5.add_vline(x=2001, line_dash="dot", line_color="#e63946", line_width=1.5,
               annotation_text="IT formal (2001)", annotation_font_size=9,
               annotation_font_color="#e63946")

fig5.write_html(CHARTS / "jel_e_detalle.html", include_plotlyjs="cdn")
print("✓ jel_e_detalle.html")


# ── Resumen en consola ─────────────────────────────────────────────────────────
print()
print("══════════════════════════════════════════════")
print("  TOP 10 CÓDIGOS JEL")
print("══════════════════════════════════════════════")
top10 = pj_full["jel_code"].value_counts().head(10)
for code, n in top10.items():
    desc = jel_cat[jel_cat["codigo"]==code]["descripcion"].values
    d = desc[0] if len(desc) and desc[0] else ""
    print(f"  {code}  {n:>4}  {d[:50] if d else ''}")
print("══════════════════════════════════════════════")
