"""
08b_autores_citados.py
-----------------------
Extrae y analiza autores citados en las referencias del subuniverso inflación.

Preguntas:
  - ¿Quiénes son los autores más citados?
  - ¿Aparecen Friedman, Lucas, Blanchard, Keynes, Galí, Woodford?
  - ¿Hay algún heterodoxo? (Lavoie, Kalecki, Minsky, Kaldor, Robinson)
  - ¿Hay estructuralistas latinoamericanos? (Prebisch, Ros, Furtado)

Output:
  data/processed/autores_citados.csv
"""

import re, sys, pandas as pd
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")

BASE    = Path(__file__).parent.parent
IN_RAW  = BASE / "data/processed/referencias_raw.csv"
OUT     = BASE / "data/processed/autores_citados.csv"

# ── Clasificación canónica de autores ─────────────────────────────────────────
# apellido_lower → (corriente, etiqueta)
AUTORES_CANON = {
    # ── Monetaristas / Nueva Clásica ──────────────────────────────────────────
    "friedman":    ("monetarista",     "Milton Friedman"),
    "phelps":      ("monetarista",     "Edmund Phelps"),
    "lucas":       ("nueva_clasica",   "Robert Lucas"),
    "sargent":     ("nueva_clasica",   "Thomas Sargent"),
    "wallace":     ("nueva_clasica",   "Neil Wallace"),
    "barro":       ("nueva_clasica",   "Robert Barro"),
    "kydland":     ("rbc",             "Finn Kydland"),
    "prescott":    ("rbc",             "Edward Prescott"),
    # ── Nueva Economía Keynesiana / DSGE ──────────────────────────────────────
    "woodford":    ("new_keynesian",   "Michael Woodford"),
    "galí":        ("new_keynesian",   "Jordi Galí"),
    "gali":        ("new_keynesian",   "Jordi Galí"),
    "gertler":     ("new_keynesian",   "Mark Gertler"),
    "clarida":     ("new_keynesian",   "Richard Clarida"),
    "blanchard":   ("new_keynesian",   "Olivier Blanchard"),
    "mankiw":      ("new_keynesian",   "N. Gregory Mankiw"),
    "taylor":      ("new_keynesian",   "John Taylor"),
    "svensson":    ("new_keynesian",   "Lars Svensson"),
    "bernanke":    ("new_keynesian",   "Ben Bernanke"),
    "christiano":  ("new_keynesian",   "Lawrence Christiano"),
    "eichenbaum":  ("new_keynesian",   "Martin Eichenbaum"),
    "smets":       ("new_keynesian",   "Frank Smets"),
    "wouters":     ("new_keynesian",   "Rafael Wouters"),
    "calvo":       ("new_keynesian",   "Guillermo Calvo"),
    "romer":       ("new_keynesian",   "David Romer"),
    "rotemberg":   ("new_keynesian",   "Julio Rotemberg"),
    "king":        ("new_keynesian",   "Robert King"),
    "goodfriend":  ("new_keynesian",   "Marvin Goodfriend"),
    "ireland":     ("new_keynesian",   "Peter Ireland"),
    "schmitt":     ("new_keynesian",   "Stephanie Schmitt-Grohé"),
    "uribe":       ("new_keynesian",   "Martín Uribe"),
    # ── Econometría / métodos ─────────────────────────────────────────────────
    "engle":       ("econometria",     "Robert Engle"),
    "granger":     ("econometria",     "Clive Granger"),
    "hamilton":    ("econometria",     "James Hamilton"),
    "sims":        ("econometria",     "Christopher Sims"),
    "dickey":      ("econometria",     "David Dickey"),
    "fuller":      ("econometria",     "Wayne Fuller"),
    "johansen":    ("econometria",     "Søren Johansen"),
    "stock":       ("econometria",     "James Stock"),
    "watson":      ("econometria",     "Mark Watson"),
    "hodrick":     ("econometria",     "Robert Hodrick"),
    "diebold":     ("econometria",     "Francis Diebold"),
    # ── Keynes original / Post-Keynesianos ────────────────────────────────────
    "keynes":      ("keynesiano_orig", "John Maynard Keynes"),
    "kalecki":     ("heterodoxo",      "Michał Kalecki"),
    "minsky":      ("heterodoxo",      "Hyman Minsky"),
    "lavoie":      ("heterodoxo",      "Marc Lavoie"),
    "godley":      ("heterodoxo",      "Wynne Godley"),
    "kaldor":      ("heterodoxo",      "Nicholas Kaldor"),
    "davidson":    ("heterodoxo",      "Paul Davidson"),
    "robinson":    ("heterodoxo",      "Joan Robinson"),
    "sraffa":      ("heterodoxo",      "Piero Sraffa"),
    "veblen":      ("heterodoxo",      "Thorstein Veblen"),
    "galbraith":   ("heterodoxo",      "John K. Galbraith"),
    # ── Estructuralistas latinoamericanos ─────────────────────────────────────
    "prebisch":    ("estructuralista", "Raúl Prebisch"),
    "furtado":     ("estructuralista", "Celso Furtado"),
    "ros":         ("estructuralista", "Jaime Ros"),
    "moreno-brid": ("estructuralista", "Juan Carlos Moreno-Brid"),
}

# ── Extraer primer apellido de una referencia ─────────────────────────────────
RE_ANIO  = re.compile(r"\b(19[5-9]\d|20[0-2]\d)\b")
RE_AUTOR = re.compile(
    r"^\s*(?:\[\d+\]\s*)?"          # opcional: [1]
    r"([A-ZÁÉÍÓÚÑÜÄÖА-Я][a-záéíóúñüäöа-я\-\']{1,25})"  # Apellido
    r"(?:,\s*[A-ZÁÉÍÓÚÑÜ]\.?[a-z]*\.?\s*(?:[A-Z]\.?\s*)*)?"  # , Nombre
)

def extraer_apellido(texto):
    """Extrae el apellido del primer autor."""
    m = RE_AUTOR.match(texto.strip())
    if m:
        return m.group(1).strip()
    return None

# ── Pipeline ──────────────────────────────────────────────────────────────────
df = pd.read_csv(IN_RAW)
print(f"Referencias cargadas: {len(df)}")

apellidos = []
for texto in df["texto_raw"].dropna():
    ap = extraer_apellido(texto)
    if ap and len(ap) > 2:
        apellidos.append(ap)

serie = pd.Series(apellidos)
conteo = serie.value_counts().reset_index()
conteo.columns = ["apellido", "n_citas"]

# Clasificar
def clasificar_autor(apellido):
    clave = apellido.lower()
    if clave in AUTORES_CANON:
        corriente, nombre = AUTORES_CANON[clave]
        return corriente, nombre
    return "no_clasificado", apellido

conteo[["corriente", "nombre_canonico"]] = conteo["apellido"].apply(
    lambda x: pd.Series(clasificar_autor(x))
)

conteo.to_csv(OUT, index=False, encoding="utf-8-sig")

# ── Reporte ───────────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print("  TOP 40 AUTORES MÁS CITADOS")
print(f"{'='*60}")
top = conteo.head(40)
for _, r in top.iterrows():
    tag = f"[{r['corriente']}]" if r['corriente'] != 'no_clasificado' else ""
    print(f"  {r['n_citas']:>3}x  {r['apellido']:<20} {tag}")

print(f"\n{'='*60}")
print("  AUTORES CANÓNICOS DETECTADOS")
print(f"{'='*60}")
canon = conteo[conteo["corriente"] != "no_clasificado"].copy()
for corriente in ["monetarista","nueva_clasica","rbc","new_keynesian",
                  "econometria","keynesiano_orig","heterodoxo","estructuralista"]:
    sub = canon[canon["corriente"] == corriente]
    if len(sub):
        print(f"\n  [{corriente.upper()}]")
        for _, r in sub.iterrows():
            print(f"    {r['n_citas']:>3}x  {r['nombre_canonico']}")

print(f"\n{'='*60}")
print("  CORRIENTES — CITAS TOTALES A AUTORES CANÓNICOS")
print(f"{'='*60}")
resumen = (canon.groupby("corriente")["n_citas"].sum()
           .sort_values(ascending=False).reset_index())
total_canon = resumen["n_citas"].sum()
for _, r in resumen.iterrows():
    print(f"  {r['corriente']:<20} {r['n_citas']:>4} citas  ({r['n_citas']/total_canon*100:.1f}%)")
