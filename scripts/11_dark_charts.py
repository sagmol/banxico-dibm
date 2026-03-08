"""
11_dark_charts.py
=================
Post-procesador que aplica dark theme a todos los charts Plotly de Fase 1.
Trabaja sobre los HTML ya generados — no modifica los scripts originales.

Estrategia:
  1. Reemplaza colores de fondo (plot_bgcolor, paper_bgcolor) en el JSON embedded
  2. Reemplaza colores problemáticos que son invisibles en dark bg (#023047)
  3. Inyecta CSS para el body + JS para Plotly.relayout() de ejes y fuentes
  4. Actualiza colorscales de heatmaps

Paleta dark (coherente con Fase 2):
  BG        = #0d1117  (fondo principal)
  BG2       = #161b22  (fondo ligeramente más claro, para subgráficas)
  TEXT      = #e6edf3  (texto principal)
  MUTED     = #7d8590  (texto secundario)
  GRID      = rgba(255,255,255,0.07)  (gridlines)
  TEAL      = #4ECDC4  (acento principal, reemplaza #023047)
  BLUE      = #74B9FF  (reemplaza #219ebc)
  PURPLE    = #A29BFE  (reemplaza #8ecae6)
  YELLOW    = #FFE66D  (reemplaza #ffb703)
  ORANGE    = #FD79A8  (reemplaza #fb8500)
  RED       = #FF6B6B  (reemplaza #e63946 en barras, conserva en anotaciones)
  GRAY      = #636e72  (reemplaza #adb5bd)
"""

import re
from pathlib import Path

BASE   = Path(__file__).resolve().parent.parent
CHARTS = BASE / "docs" / "charts"

# ── Archivos a procesar ────────────────────────────────────────────────────────
TARGETS = [
    "temporal_produccion_anual.html",
    "temporal_produccion_decada.html",
    "temporal_acumulado.html",
    "temporal_autores_activos.html",
    "temporal_jel_grupos.html",
    "jel_top20.html",
    "jel_grupos_barras.html",
    "jel_heatmap_periodo.html",
    "jel_top_por_periodo.html",
    "jel_e_detalle.html",
    "red_coautoria.html",
    "autores_top_productivos.html",
    "autores_centralidad.html",
    "clusters_scatter.html",
    "clusters_palabras.html",
    "clusters_distribucion.html",
    "clusters_evolucion.html",
    "clusters_calor_periodo.html",
]

# ── Reemplazos de color en el JSON embedded ────────────────────────────────────
# Orden importa: más específicos primero
COLOR_SUBS = [
    # Fondo del chart principal y del papel
    ('"paper_bgcolor":"white"',   '"paper_bgcolor":"#0d1117"'),
    ('"paper_bgcolor":"#fafafa"', '"paper_bgcolor":"#0d1117"'),
    ('"paper_bgcolor":"#E5ECF6"', '"paper_bgcolor":"#0d1117"'),
    ('"plot_bgcolor":"white"',    '"plot_bgcolor":"#0d1117"'),
    ('"plot_bgcolor":"#fafafa"',  '"plot_bgcolor":"#0d1117"'),
    ('"plot_bgcolor":"#E5ECF6"',  '"plot_bgcolor":"#0d1117"'),

    # Gridlines de ejes (template Plotly por defecto)
    ('"gridcolor":"white"',   '"gridcolor":"rgba(255,255,255,0.07)"'),
    ('"gridcolor":"#eeeeee"', '"gridcolor":"rgba(255,255,255,0.07)"'),

    # Color de fuente principal (Plotly default dark on light)
    ('"color":"#2a3f5f"', '"color":"#e6edf3"'),

    # Colores de barras / líneas problemáticos (oscuros → invisibles en dark bg)
    ('"color":"#023047"',     '"color":"#4ECDC4"'),
    ('"color":"#219ebc"',     '"color":"#74B9FF"'),
    ('"color":"#8ecae6"',     '"color":"#A29BFE"'),
    ('"color":"#457b9d"',     '"color":"#6CB4F5"'),
    ('"color":"#a8dadc"',     '"color":"#55EFC4"'),
    ('"color":"#ffb703"',     '"color":"#FFE66D"'),
    ('"color":"#fb8500"',     '"color":"#FD79A8"'),
    ('"color":"#adb5bd"',     '"color":"#636e72"'),

    # marker_color (mismo patrón pero en marker objects)
    ('"marker_color":"#023047"', '"marker_color":"#4ECDC4"'),
    ('"marker_color":"#219ebc"', '"marker_color":"#74B9FF"'),
    ('"marker_color":"#8ecae6"', '"marker_color":"#A29BFE"'),

    # En arrays de color (heatmaps y scatter)
    ('"#023047"', '"#4ECDC4"'),   # dark navy → teal
    ('"#219ebc"', '"#74B9FF"'),   # medium blue → light blue
    ('"#8ecae6"', '"#A29BFE"'),   # pale blue → purple
    ('"#ffb703"', '"#FFE66D"'),   # amber → bright yellow
    ('"#fb8500"', '"#FD79A8"'),   # orange → pink
    ('"#457b9d"', '"#6CB4F5"'),   # blue → lighter
    ('"#a8dadc"', '"#55EFC4"'),   # pale teal → bright teal
    ('"#adb5bd"', '"#636e72"'),   # gray → darker gray
    ('"#f8f9fa"', '"#161b22"'),   # near-white start in heatmap colorscale
    ('"#fafafa"', '"#161b22"'),

    # Fondo de anotaciones (cajas con texto sobre el gráfico)
    ('"bgcolor":"rgba(255,255,255,0.7)"',  '"bgcolor":"rgba(13,17,23,0.9)"'),
    ('"bgcolor":"rgba(255,255,255,0.85)"', '"bgcolor":"rgba(13,17,23,0.9)"'),
    ('"bgcolor":"rgba(255,255,255,0.8)"',  '"bgcolor":"rgba(13,17,23,0.9)"'),

    # Texto de anotaciones (oscuro sobre blanco → claro sobre oscuro)
    ('"color":"#444"', '"color":"#cdd9e5"'),
    ('"color":"#666"', '"color":"#7d8590"'),
    ('"color":"#555"', '"color":"#cdd9e5"'),

    # Fuentes serif → Inter (coherente con Fase 2)
    ('"family":"Georgia, serif"', '"family":"Inter, system-ui, sans-serif"'),
    ('"family":"Georgia,serif"',  '"family":"Inter, system-ui, sans-serif"'),

    # Colores internos del template Plotly (fondo de celda/polar en el JSON template)
    ('"color":"#E5ECF6"', '"color":"#1c2433"'),  # background polar/template
    ('"bgcolor":"#E5ECF6"', '"bgcolor":"#0d1117"'),
    ('"bgcolor":"white"', '"bgcolor":"#0d1117"'),

    # Borde de tabla (Plotly default)
    ('"color":"#E5ECF6"', '"color":"#161b22"'),

    # Header de tabla
    ('"color":"#C8D4E3"', '"color":"#1e2738"'),

    # Relleno de tabla (celda)
    ('"color":"#EBF0F8"', '"color":"#0d1117"'),

    # Línea de borde de barras
    ('"color":"#E5ECF6","width":0.5', '"color":"#1c2433","width":0.5'),
]

# ── CSS + JS inyectable ────────────────────────────────────────────────────────
DARK_INJECT = '''<style>
html, body {
  background: #0d1117 !important;
  margin: 0; padding: 0;
  font-family: 'Inter', system-ui, sans-serif;
}
.plotly-graph-div { border-radius: 8px; }
</style>
<script>
document.addEventListener('DOMContentLoaded', function() {
  setTimeout(function() {
    var divs = document.querySelectorAll('.plotly-graph-div');
    divs.forEach(function(div) {
      try {
        var upd = {
          paper_bgcolor: '#0d1117',
          plot_bgcolor:  '#0d1117',
          'font.color':  '#e6edf3',
          'font.family': 'Inter, system-ui, sans-serif',
          'title.font.color': '#e6edf3',
        };
        // Actualizar todos los ejes posibles (hasta 8 por subplot)
        var axes = ['','2','3','4','5','6','7','8'];
        axes.forEach(function(i) {
          ['xaxis','yaxis'].forEach(function(ax) {
            var a = ax + i;
            upd[a+'.gridcolor']         = 'rgba(255,255,255,0.07)';
            upd[a+'.tickfont.color']    = '#7d8590';
            upd[a+'.title.font.color']  = '#9aadba';
            upd[a+'.linecolor']         = 'rgba(255,255,255,0.08)';
            upd[a+'.zerolinecolor']     = 'rgba(255,255,255,0.08)';
          });
        });
        // Colorbar
        upd['coloraxis.colorbar.tickfont.color'] = '#7d8590';
        upd['coloraxis.colorbar.title.font.color'] = '#9aadba';
        Plotly.relayout(div, upd);
      } catch(e) {}
    });
  }, 150);
});
</script>'''

# ── Procesador ─────────────────────────────────────────────────────────────────
def apply_dark_theme(html_path: Path) -> bool:
    """Aplica dark theme a un archivo HTML de Plotly. Devuelve True si éxito."""
    try:
        content = html_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"  ERR Error leyendo {html_path.name}: {e}")
        return False

    original = content

    # Aplicar reemplazos de color
    for old, new in COLOR_SUBS:
        content = content.replace(old, new)

    # Inyectar CSS y JS antes del </body>
    # Si ya fue procesado, no duplicar
    if 'background: #0d1117 !important' not in content:
        content = content.replace('</body>', DARK_INJECT + '\n</body>')
    else:
        # Actualizar el bloque si ya existe (re-procesado)
        content = re.sub(
            r'<style>\s*html, body \{[^}]+\}[^<]*</style>\s*<script>.*?</script>',
            DARK_INJECT,
            content, flags=re.DOTALL
        )

    if content == original:
        print(f"  ~~ {html_path.name}  (sin cambios)")
        return True

    html_path.write_text(content, encoding="utf-8")
    # Contar reemplazos aproximados
    n_changes = sum(original.count(old) for old, _ in COLOR_SUBS if old in original)
    print(f"  OK {html_path.name}  ({n_changes} sustituciones de color)")
    return True


# ── Main ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("11_dark_charts.py — Aplicando dark theme a charts Plotly")
    print("=" * 60)

    ok = 0
    for fname in TARGETS:
        path = CHARTS / fname
        if not path.exists():
            print(f"  !! No encontrado: {fname}")
            continue
        if apply_dark_theme(path):
            ok += 1

    print(f"\n{'=' * 60}")
    print(f"Procesados: {ok}/{len(TARGETS)} archivos")
    print(f"Guardados en: {CHARTS}")
