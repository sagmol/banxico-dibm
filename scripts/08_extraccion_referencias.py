"""
08_extraccion_referencias.py  (v2)
------------------------------------
Extrae y clasifica referencias bibliográficas de los PDFs del subuniverso inflación.

Mejoras v2:
  - Taxonomía desagregada en 11 sub-categorías
  - Matching con y sin espacios (problema PDF frecuente)
  - Abreviaciones canónicas (AER, JME, JPE, QJE…)
  - Filtro de falsos positivos (tablas, ecuaciones, notas)

Outputs:
  data/processed/referencias_raw.csv      — una fila por referencia
  data/processed/referencias_journals.csv — frecuencia de journals por categoría
  data/processed/referencias_resumen.csv  — métricas por paper
"""

import re, sys, pdfplumber, pandas as pd
from pathlib import Path

# ── Rutas ─────────────────────────────────────────────────────────────────────
BASE     = Path(__file__).parent.parent
PDF_DIR  = BASE / "data" / "pdfs" / "inflacion"
LOG_FILE = BASE / "data" / "processed" / "pdfs_log.csv"
OUT_RAW  = BASE / "data" / "processed" / "referencias_raw.csv"
OUT_JOUR = BASE / "data" / "processed" / "referencias_journals.csv"
OUT_RES  = BASE / "data" / "processed" / "referencias_resumen.csv"

# ── Taxonomía desagregada ──────────────────────────────────────────────────────
# Cada entrada: fragmento_lowercase → (categoria, subcategoria, nombre_canonico)
# Se registran variantes: con espacios, sin espacios, abreviadas, con puntos

JOURNALS = [
    # ── TIER 1 GENERALIST ─────────────────────────────────────────────────────
    ("american economic review",            "ortodoxo", "tier1_generalist",    "American Economic Review"),
    ("am. econ. rev",                       "ortodoxo", "tier1_generalist",    "American Economic Review"),
    (" aer ",                               "ortodoxo", "tier1_generalist",    "American Economic Review"),
    ("journal of political economy",        "ortodoxo", "tier1_generalist",    "Journal of Political Economy"),
    ("journalofpoliticaleconomy",           "ortodoxo", "tier1_generalist",    "Journal of Political Economy"),
    (" jpe ",                               "ortodoxo", "tier1_generalist",    "Journal of Political Economy"),
    ("quarterly journal of economics",      "ortodoxo", "tier1_generalist",    "Quarterly Journal of Economics"),
    ("quarterlyjournal",                    "ortodoxo", "tier1_generalist",    "Quarterly Journal of Economics"),
    (" qje ",                               "ortodoxo", "tier1_generalist",    "Quarterly Journal of Economics"),
    ("review of economic studies",          "ortodoxo", "tier1_generalist",    "Review of Economic Studies"),
    ("reviewofeconomicstudies",             "ortodoxo", "tier1_generalist",    "Review of Economic Studies"),
    ("rev. econ. stud",                     "ortodoxo", "tier1_generalist",    "Review of Economic Studies"),
    (" restud",                             "ortodoxo", "tier1_generalist",    "Review of Economic Studies"),
    ("econometrica",                        "ortodoxo", "tier1_generalist",    "Econometrica"),

    # ── MACRO / POLÍTICA MONETARIA ────────────────────────────────────────────
    ("journal of monetary economics",       "ortodoxo", "macro_monetario",     "Journal of Monetary Economics"),
    ("journalofmonetaryeconomics",          "ortodoxo", "macro_monetario",     "Journal of Monetary Economics"),
    ("j. monet. econ",                      "ortodoxo", "macro_monetario",     "Journal of Monetary Economics"),
    (" jme ",                               "ortodoxo", "macro_monetario",     "Journal of Monetary Economics"),
    ("journal of money, credit",            "ortodoxo", "macro_monetario",     "Journal of Money, Credit and Banking"),
    ("journalofmoney",                      "ortodoxo", "macro_monetario",     "Journal of Money, Credit and Banking"),
    (" jmcb",                               "ortodoxo", "macro_monetario",     "Journal of Money, Credit and Banking"),
    ("journal of macroeconomics",           "ortodoxo", "macro_monetario",     "Journal of Macroeconomics"),
    ("journalofmacroeconomics",             "ortodoxo", "macro_monetario",     "Journal of Macroeconomics"),
    ("international journal of central",    "ortodoxo", "macro_monetario",     "International Journal of Central Banking"),
    (" ijcb",                               "ortodoxo", "macro_monetario",     "International Journal of Central Banking"),
    ("journal of economic dynamics",        "ortodoxo", "macro_monetario",     "Journal of Economic Dynamics and Control"),
    ("journalofeconomicdynamics",           "ortodoxo", "macro_monetario",     "Journal of Economic Dynamics and Control"),
    ("american economic journal: macro",    "ortodoxo", "macro_monetario",     "AEJ: Macroeconomics"),
    ("aej: macro",                          "ortodoxo", "macro_monetario",     "AEJ: Macroeconomics"),
    ("aej macro",                           "ortodoxo", "macro_monetario",     "AEJ: Macroeconomics"),
    ("brookings papers",                    "ortodoxo", "macro_monetario",     "Brookings Papers on Economic Activity"),

    # ── ECONOMETRÍA / MÉTODOS ─────────────────────────────────────────────────
    ("journal of econometrics",             "ortodoxo", "econometria",         "Journal of Econometrics"),
    ("journalofeconometrics",               "ortodoxo", "econometria",         "Journal of Econometrics"),
    ("journal of applied econometrics",     "ortodoxo", "econometria",         "Journal of Applied Econometrics"),
    ("journalofappliedeconometrics",        "ortodoxo", "econometria",         "Journal of Applied Econometrics"),
    ("review of economics and statistics",  "ortodoxo", "econometria",         "Review of Economics and Statistics"),
    ("reviewofeconomicsandstatistics",      "ortodoxo", "econometria",         "Review of Economics and Statistics"),
    ("rev. econ. stat",                     "ortodoxo", "econometria",         "Review of Economics and Statistics"),
    (" restat",                             "ortodoxo", "econometria",         "Review of Economics and Statistics"),
    ("oxford bulletin",                     "ortodoxo", "econometria",         "Oxford Bulletin of Economics and Statistics"),
    ("econometric theory",                  "ortodoxo", "econometria",         "Econometric Theory"),
    ("econometric reviews",                 "ortodoxo", "econometria",         "Econometric Reviews"),
    ("journal of business & economic stat", "ortodoxo", "econometria",         "Journal of Business & Economic Statistics"),
    ("journal of business and economic",    "ortodoxo", "econometria",         "Journal of Business & Economic Statistics"),
    ("journalofbusiness",                   "ortodoxo", "econometria",         "Journal of Business & Economic Statistics"),

    # ── FINANZAS ──────────────────────────────────────────────────────────────
    ("journal of finance",                  "ortodoxo", "finanzas",            "Journal of Finance"),
    ("journaloffinance",                    "ortodoxo", "finanzas",            "Journal of Finance"),
    ("journal of financial economics",      "ortodoxo", "finanzas",            "Journal of Financial Economics"),
    ("journaloffinancialeconomics",         "ortodoxo", "finanzas",            "Journal of Financial Economics"),
    ("review of financial studies",         "ortodoxo", "finanzas",            "Review of Financial Studies"),
    ("reviewoffinancialstudies",            "ortodoxo", "finanzas",            "Review of Financial Studies"),
    ("journal of financial intermediation", "ortodoxo", "finanzas",            "Journal of Financial Intermediation"),
    ("journal of banking and finance",      "ortodoxo", "finanzas",            "Journal of Banking and Finance"),
    ("journalofbankingandfinance",          "ortodoxo", "finanzas",            "Journal of Banking and Finance"),
    ("journal of banking & finance",        "ortodoxo", "finanzas",            "Journal of Banking and Finance"),
    ("finance research letters",            "ortodoxo", "finanzas",            "Finance Research Letters"),
    ("financeresearchletters",              "ortodoxo", "finanzas",            "Finance Research Letters"),
    ("review of finance",                   "ortodoxo", "finanzas",            "Review of Finance"),
    ("reviewoffinance",                     "ortodoxo", "finanzas",            "Review of Finance"),
    ("journal of risk",                     "ortodoxo", "finanzas",            "Journal of Risk"),
    ("journal of risk and insurance",       "ortodoxo", "finanzas",            "Journal of Risk and Insurance"),
    ("journal of futures markets",          "ortodoxo", "finanzas",            "Journal of Futures Markets"),

    # ── INTERNACIONAL ─────────────────────────────────────────────────────────
    ("journal of international economics",  "ortodoxo", "internacional",       "Journal of International Economics"),
    ("journalofinternationaleconomics",     "ortodoxo", "internacional",       "Journal of International Economics"),
    ("journal of international money",      "ortodoxo", "internacional",       "Journal of International Money and Finance"),

    # ── OTROS MAINSTREAM ──────────────────────────────────────────────────────
    ("economic journal",                    "ortodoxo", "otros_mainstream",    "Economic Journal"),
    ("economicjournal",                     "ortodoxo", "otros_mainstream",    "Economic Journal"),
    ("european economic review",            "ortodoxo", "otros_mainstream",    "European Economic Review"),
    ("europeaneconomicreview",              "ortodoxo", "otros_mainstream",    "European Economic Review"),
    ("journal of the european economic",    "ortodoxo", "otros_mainstream",    "Journal of the European Economic Association"),
    (" jeea",                               "ortodoxo", "otros_mainstream",    "Journal of the European Economic Association"),
    ("journal of economic perspectives",    "ortodoxo", "otros_mainstream",    "Journal of Economic Perspectives"),
    ("journalofeconomicperspectives",       "ortodoxo", "otros_mainstream",    "Journal of Economic Perspectives"),
    ("journal of economic literature",      "ortodoxo", "otros_mainstream",    "Journal of Economic Literature"),
    ("journal of economic theory",          "ortodoxo", "otros_mainstream",    "Journal of Economic Theory"),
    ("rand journal",                        "ortodoxo", "otros_mainstream",    "RAND Journal of Economics"),
    ("oxford economic papers",              "ortodoxo", "otros_mainstream",    "Oxford Economic Papers"),
    ("scandinavian journal of economics",   "ortodoxo", "otros_mainstream",    "Scandinavian Journal of Economics"),
    ("el trimestre económico",              "ortodoxo", "otros_mainstream",    "El Trimestre Económico"),
    ("el trimestre economico",              "ortodoxo", "otros_mainstream",    "El Trimestre Económico"),
    ("economia mexicana",                   "ortodoxo", "otros_mainstream",    "Economía Mexicana"),
    ("latin american journal of economics", "ortodoxo", "otros_mainstream",    "Latin American Journal of Economics"),
    ("cuadernos de economía",               "ortodoxo", "otros_mainstream",    "Cuadernos de Economía"),
    ("journal of development economics",    "ortodoxo", "otros_mainstream",    "Journal of Development Economics"),
    ("games and economic behavior",         "ortodoxo", "otros_mainstream",    "Games and Economic Behavior"),
    # — journals frecuentes no capturados antes —
    ("economics letters",                   "ortodoxo", "otros_mainstream",    "Economics Letters"),
    ("economicsletters",                    "ortodoxo", "otros_mainstream",    "Economics Letters"),
    ("economica",                           "ortodoxo", "otros_mainstream",    "Economica"),
    ("economic policy",                     "ortodoxo", "otros_mainstream",    "Economic Policy"),
    ("economicpolicy",                      "ortodoxo", "otros_mainstream",    "Economic Policy"),
    ("journal of economic surveys",         "ortodoxo", "otros_mainstream",    "Journal of Economic Surveys"),
    ("journalofeconomicsurveys",            "ortodoxo", "otros_mainstream",    "Journal of Economic Surveys"),
    ("carnegie-rochester",                  "ortodoxo", "otros_mainstream",    "Carnegie-Rochester Conference Series"),
    ("carnegie rochester",                  "ortodoxo", "otros_mainstream",    "Carnegie-Rochester Conference Series"),
    ("journal of urban economics",          "ortodoxo", "otros_mainstream",    "Journal of Urban Economics"),
    ("journal of labor economics",          "ortodoxo", "otros_mainstream",    "Journal of Labor Economics"),
    ("journal of public economics",         "ortodoxo", "otros_mainstream",    "Journal of Public Economics"),
    ("american economic journal",           "ortodoxo", "otros_mainstream",    "American Economic Journal"),
    ("monetaria",                           "institucional", "wp_bc_latam",    "Monetaria (CEMLA)"),

    # ── WP BANXICO (AUTOCITAS) ────────────────────────────────────────────────
    ("banco de m",                          "institucional", "wp_banxico",      "Banco de México WP"),
    ("banxico",                             "institucional", "wp_banxico",      "Banco de México WP"),
    ("working paper banco",                 "institucional", "wp_banxico",      "Banco de México WP"),

    # ── WP MULTILATERALES ─────────────────────────────────────────────────────
    ("nber working",                        "institucional", "wp_multilateral", "NBER Working Paper"),
    ("nber w",                              "institucional", "wp_multilateral", "NBER Working Paper"),
    ("nber macroeconomics annual",          "institucional", "wp_multilateral", "NBER Macroeconomics Annual"),
    ("imf working",                         "institucional", "wp_multilateral", "IMF Working Paper"),
    ("imf staff",                           "institucional", "wp_multilateral", "IMF Staff Papers"),
    ("imf sta",                             "institucional", "wp_multilateral", "IMF Staff Papers"),   # encoding roto: Sta¤
    ("international monetary fund",         "institucional", "wp_multilateral", "IMF Working Paper"),
    ("bis working",                         "institucional", "wp_multilateral", "BIS Working Paper"),
    ("bank of international settlements",   "institucional", "wp_multilateral", "BIS Working Paper"),
    ("world bank",                          "institucional", "wp_multilateral", "World Bank"),
    ("cepr discussion",                     "institucional", "wp_multilateral", "CEPR Discussion Paper"),
    ("cepr dp",                             "institucional", "wp_multilateral", "CEPR Discussion Paper"),
    ("iza discussion",                      "institucional", "wp_multilateral", "IZA Discussion Paper"),
    ("iza dp",                              "institucional", "wp_multilateral", "IZA Discussion Paper"),

    # ── WP BC DESARROLLADOS ───────────────────────────────────────────────────
    ("federal reserve",                     "institucional", "wp_bc_avanzado",  "Federal Reserve"),
    ("fed reserve",                         "institucional", "wp_bc_avanzado",  "Federal Reserve"),
    ("ecb working",                         "institucional", "wp_bc_avanzado",  "ECB Working Paper"),
    ("european central bank",               "institucional", "wp_bc_avanzado",  "ECB Working Paper"),
    ("bank of england",                     "institucional", "wp_bc_avanzado",  "Bank of England"),
    ("banco de españa",                     "institucional", "wp_bc_avanzado",  "Banco de España"),
    ("banco de espana",                     "institucional", "wp_bc_avanzado",  "Banco de España"),
    ("banco de espa",                       "institucional", "wp_bc_avanzado",  "Banco de España"),  # encoding roto
    ("bank of spain",                       "institucional", "wp_bc_avanzado",  "Banco de España"),
    ("bank of canada",                      "institucional", "wp_bc_avanzado",  "Bank of Canada"),
    ("reserve bank",                        "institucional", "wp_bc_avanzado",  "Reserve Bank"),
    ("riksbank",                            "institucional", "wp_bc_avanzado",  "Sveriges Riksbank"),
    ("norges bank",                         "institucional", "wp_bc_avanzado",  "Norges Bank"),
    ("bundesbank",                          "institucional", "wp_bc_avanzado",  "Deutsche Bundesbank"),

    # ── WP BC LATINOAMÉRICA ───────────────────────────────────────────────────
    ("cemla",                               "institucional", "wp_bc_latam",     "CEMLA"),
    ("banco central de chile",              "institucional", "wp_bc_latam",     "Banco Central de Chile"),
    ("banco central chile",                 "institucional", "wp_bc_latam",     "Banco Central de Chile"),
    ("banco de la república",               "institucional", "wp_bc_latam",     "Banco de la República (Colombia)"),
    ("banco central do brasil",             "institucional", "wp_bc_latam",     "Banco Central do Brasil"),
    ("banco central de reserva",            "institucional", "wp_bc_latam",     "Banco Central de Reserva"),

    # ── CEPAL / ESTRUCTURALISTA ───────────────────────────────────────────────
    ("cepal",                               "estructuralista", "cepal",         "CEPAL/ECLAC"),
    ("eclac",                               "estructuralista", "cepal",         "CEPAL/ECLAC"),
    ("revista cepal",                       "estructuralista", "cepal",         "Revista CEPAL"),

    # ── HETERODOXO ────────────────────────────────────────────────────────────
    ("journal of post keynesian",           "heterodoxo", "post_keynesiano",    "Journal of Post Keynesian Economics"),
    ("cambridge journal of economics",      "heterodoxo", "post_keynesiano",    "Cambridge Journal of Economics"),
    ("review of political economy",         "heterodoxo", "post_keynesiano",    "Review of Political Economy"),
    ("metroeconomica",                      "heterodoxo", "post_keynesiano",    "Metroeconomica"),
    ("european journal of economics and economic policies", "heterodoxo", "post_keynesiano", "EJEEP"),
    ("journal of economic issues",          "heterodoxo", "institucionalista",  "Journal of Economic Issues"),
    ("journal of evolutionary economics",   "heterodoxo", "institucionalista",  "Journal of Evolutionary Economics"),
    ("review of radical",                   "heterodoxo", "marxista",           "Review of Radical Political Economics"),
    ("capital & class",                     "heterodoxo", "marxista",           "Capital & Class"),
    ("ecological economics",                "heterodoxo", "ecologico",          "Ecological Economics"),
    ("feminist economics",                  "heterodoxo", "feminista",          "Feminist Economics"),
]

# ── Editoriales mainstream (libros) ───────────────────────────────────────────
# Presencia de editorial + ausencia de journal → libro mainstream
EDITORIALES_MAINSTREAM = [
    "princeton university press",
    "princetonuniversitypress",
    "mit press",
    "cambridge university press",
    "cambridgeuniversitypress",
    "oxford university press",
    "oxforduniversitypress",
    "university of chicago press",
    "harvard university press",
    "brookings institution press",
    "mcgraw-hill",
    "north-holland",
    "elsevier",          # mayoría de journals Elsevier son mainstream
    "springer",
    "wiley",
]

EDITORIALES_HETERODOXAS = [
    "edward elgar",      # editorial preferida de heterodoxos
    "routledge",         # publica tanto orthodox como heterodox, solo si hay señal adicional
]

def clasificar(texto):
    t = texto.lower().replace("\n", " ")
    # versión sin espacios para PDFs con texto pegado
    t_nospace = re.sub(r"\s+", "", t)

    # 1) Buscar journal conocido
    for fragmento, cat, subcat, nombre in JOURNALS:
        frag_nospace = re.sub(r"\s+", "", fragmento)
        if fragmento in t or frag_nospace in t_nospace:
            return cat, subcat, nombre

    # 2) Si no matchea journal, intentar clasificar por editorial (libro)
    for ed in EDITORIALES_HETERODOXAS:
        if ed in t:
            return "heterodoxo", "libro_heterodoxo", f"Libro ({ed.title()})"

    for ed in EDITORIALES_MAINSTREAM:
        if ed in t or re.sub(r"\s+", "", ed) in t_nospace:
            return "ortodoxo", "libro_mainstream", f"Libro ({ed.title()})"

    return "desconocido", "desconocido", None

# ── Filtros de calidad ─────────────────────────────────────────────────────────
RE_ANIO    = re.compile(r"\b(19[5-9]\d|20[0-2]\d)\b")
RE_TABLA   = re.compile(r"^\s*(table|figura|figure|cuadro|notas?:|notes?:|source|fuente)", re.I)
RE_NUMERO  = re.compile(r"^\s*[\d\.\*\-\+\[\]\(\)]{4,}")  # línea que empieza con números
RE_FORMULA = re.compile(r"[=∑∫∂βαγσεµ]{2,}|cid:\d+")

def es_referencia_valida(texto):
    """Descarta líneas que son tablas, fórmulas, notas o muy cortas."""
    if len(texto) < 30:
        return False
    if RE_TABLA.match(texto):
        return False
    if RE_NUMERO.match(texto):
        return False
    if RE_FORMULA.search(texto):
        return False
    # Debe contener al menos un año o una coma (apellido, nombre)
    if not RE_ANIO.search(texto) and "," not in texto:
        return False
    return True

# ── Extracción de texto ────────────────────────────────────────────────────────
RE_SEC = re.compile(
    r"^\s*(references|bibliography|bibliograf[íi]a|referencias)\s*$",
    re.IGNORECASE | re.MULTILINE
)

def extraer_texto_pdf(ruta):
    paginas = []
    try:
        with pdfplumber.open(ruta) as pdf:
            for pag in pdf.pages:
                t = pag.extract_text()
                if t:
                    paginas.append(t)
    except Exception as e:
        return None, str(e)
    return "\n".join(paginas), None

def encontrar_bloque_referencias(texto):
    m = RE_SEC.search(texto)
    if not m:
        return None
    bloque = texto[m.start():]
    # Cortar si hay apéndice después
    corte = re.search(r"\n\s*(appendix|apéndice|ap[eé]ndice|notes\s*\n|footnotes)\s*\n",
                      bloque, re.IGNORECASE)
    if corte and corte.start() > 300:
        bloque = bloque[:corte.start()]
    return bloque

def split_referencias(bloque):
    """Separa referencias individuales con heurística doble."""
    lineas = bloque.split("\n")[1:]  # omitir header
    refs, actual = [], []

    for linea in lineas:
        s = linea.strip()
        if not s:
            # Línea en blanco → posible fin de referencia
            if actual and len(" ".join(actual)) > 40:
                refs.append(" ".join(actual))
                actual = []
            continue

        # Nueva referencia numerada: [1] ó 1.
        es_num = bool(re.match(r"^\[?\d{1,3}\]?\.?\s+[A-Z]", s))
        # Nueva referencia autor-año: Apellido, + año en los próximos 60 chars
        es_autor = (bool(re.match(r"^[A-ZÁÉÍÓÚÑÜ][a-záéíóúñü]{2,},\s*[A-Z]", s))
                    and bool(RE_ANIO.search(s[:80])))

        if (es_num or es_autor) and actual:
            texto_ref = " ".join(actual).strip()
            if es_referencia_valida(texto_ref):
                refs.append(texto_ref)
            actual = [s]
        else:
            actual.append(s)

    if actual:
        texto_ref = " ".join(actual).strip()
        if es_referencia_valida(texto_ref):
            refs.append(texto_ref)

    return refs

# ── Pipeline ───────────────────────────────────────────────────────────────────
def procesar_pdfs():
    log    = pd.read_csv(LOG_FILE)
    pdfs_ok = log[log["status"] == "ok"]["clave"].tolist()
    print(f"PDFs a procesar: {len(pdfs_ok)}\n")

    todas_refs, resumenes, errores = [], [], []

    for i, clave in enumerate(pdfs_ok, 1):
        ruta = PDF_DIR / f"{clave}.pdf"
        sys.stdout.write(f"\r[{i:3d}/{len(pdfs_ok)}] {clave:<12} ")
        sys.stdout.flush()

        if not ruta.exists():
            errores.append({"clave": clave, "error": "no encontrado"})
            continue

        texto, err = extraer_texto_pdf(ruta)
        if err or not texto:
            errores.append({"clave": clave, "error": err or "vacío"})
            print("ERROR extracción")
            continue

        bloque = encontrar_bloque_referencias(texto)
        if not bloque:
            errores.append({"clave": clave, "error": "sin sección referencias"})
            print("sin refs")
            continue

        refs = split_referencias(bloque)
        n = len(refs)
        print(f"{n:>3} refs")

        for j, ref_texto in enumerate(refs):
            cat, subcat, journal = clasificar(ref_texto)
            años = RE_ANIO.findall(ref_texto)
            todas_refs.append({
                "clave_paper":      clave,
                "num_ref":          j + 1,
                "texto_raw":        ref_texto[:400],
                "anio_citado":      años[0] if años else None,
                "categoria":        cat,
                "subcategoria":     subcat,
                "journal_detectado": journal,
            })

        n_cls = sum(1 for r in refs if clasificar(r)[0] != "desconocido")
        resumenes.append({
            "clave_paper":    clave,
            "n_referencias":  n,
            "n_clasificadas": n_cls,
            "pct_clasificado": round(n_cls / n * 100, 1) if n else 0,
        })

    # ── Guardar ───────────────────────────────────────────────────────────────
    df_refs = pd.DataFrame(todas_refs)
    df_refs.to_csv(OUT_RAW,  index=False, encoding="utf-8-sig")

    conocidos = df_refs[df_refs["categoria"] != "desconocido"]
    freq = (conocidos
            .groupby(["journal_detectado", "categoria", "subcategoria"])
            .size().reset_index(name="n_citas")
            .sort_values("n_citas", ascending=False))
    freq.to_csv(OUT_JOUR, index=False, encoding="utf-8-sig")

    pd.DataFrame(resumenes).to_csv(OUT_RES, index=False, encoding="utf-8-sig")

    # ── Resumen ───────────────────────────────────────────────────────────────
    total_refs = len(df_refs)
    total_cls  = len(conocidos)
    print(f"\n{'='*65}")
    print(f"  Papers procesados    : {len(resumenes)}")
    print(f"  Referencias totales  : {total_refs}")
    print(f"  Clasificadas         : {total_cls}  ({total_cls/total_refs*100:.1f}%)")
    print(f"\n  TOP 20 JOURNALS:")
    print(freq.head(20)[["journal_detectado","subcategoria","n_citas"]].to_string(index=False))
    print(f"\n  POR CATEGORÍA:")
    cat_sum = (conocidos.groupby(["categoria","subcategoria"])
               .size().reset_index(name="n")
               .sort_values("n", ascending=False))
    for _, r in cat_sum.iterrows():
        pct = r["n"] / total_cls * 100
        print(f"    {r['categoria']:<16} {r['subcategoria']:<20} {r['n']:>4}  ({pct:.1f}%)")
    print(f"\n  Errores: {len(errores)}")
    print(f"{'='*65}")

if __name__ == "__main__":
    procesar_pdfs()
