# Documentacion Tecnica: Proyecto DIBM Banxico

Analisis bibliometrico del corpus DIBM, Banco de Mexico (1978-2025)

---

## Fuente de datos

- API Banxico: https://www.banxico.org.mx/DIBM/web/documentos.json
- 563 documentos, 447 autores unicos, 379 codigos JEL
- PDFs disponibles para ~64% del corpus

---

## Stack tecnologico

| Paquete | Para que |
|---|---|
| pandas | limpieza y datos tabulares |
| pdfplumber | extraccion texto de PDFs |
| networkx | redes coautoria y co-citacion |
| sklearn | NMF topic modeling + t-SNE |
| nltk/gensim | NLP: stopwords, tokenizacion |
| plotly | charts estaticos dark theme |
| sqlite3 | base de datos corpus |
| D3.js v7 | redes interactivas en browser |

---

## Scripts (en orden de ejecucion)

### Fase 1 - Corpus
01_limpieza.py          -> papers.csv, paper_authors.csv, corpus.db
02_analisis_temporal.py -> charts de produccion anual/decadal
03_analisis_jel.py      -> jel_top20.html, heatmaps
04_red_coautoria.py     -> coautoria_red.json, red_coautoria.html
05_clusters_tematicos.py-> tsne_clusters.json, clusters_scatter.html
11_dark_charts.py       -> post-procesador dark theme Plotly

### Fase 2 - Referencias bibliograficas
07_descarga_pdfs.py     -> 104 PDFs inflacion (JEL E3x, E5x)
08_extraccion_referencias.py -> referencias_clasificadas.csv (11 cats)
09_red_citas.py         -> autores_red.json, journals_red.json

### Fase 3 - NLP y analisis avanzado
10a_nlp_abstracts.py    -> nlp_vocab_periodo.json, nlp_vocab_anio.json
10b_temporal_citas.py   -> temporal_citas.json
10c_autocitacion_calvo.py -> autocitacion.json
10d_conceptos_especificos.py -> nlp_conceptos_anio.json (11 conceptos NK-DSGE/anio)
10e_citation_vintage.py -> citation_vintage.json (edad referencias)
10f_author_dsge.py      -> author_dsge.json (nk_score por autor)
10g_debates_papers.py   -> debates_papers.json (papers por debate)

---

## Tecnicas analiticas

NMF (Non-negative Matrix Factorization)
  - Sobre matriz TF-IDF de 501 abstracts, 10 topicos
  - Cada paper asignado al topico de mayor peso
  - Ventaja vs LDA: mas interpretable con corpus pequeno

t-SNE
  - Reduccion 2D de la misma matriz TF-IDF
  - Parametros: perplexity=30, n_iter=1000
  - Proximidad = similitud tematica relativa (no distancias absolutas)

Community detection
  - Pre-computado (JSON): Louvain via networkx
  - Version JS: label propagation (25 iteraciones)
  - Resultado: 57 comunidades en 184 nodos

Clasificacion de referencias
  - Taxonomia manual de 11 subcategorias
  - 1,911 referencias de 85 papers, 70.5% clasificadas
  - No clasificadas: referencias incompletas en el PDF

Busqueda textual en abstracts
  - Matching exacto sin stemming (para controlar falsos positivos)
  - Lista curada de ~25 terminos ortodoxos y ~15 heterodoxos
  - ADVERTENCIA: distribution y power son falsos positivos en contexto mainstream

---

## Taxonomia de referencias (11 categorias)

tier1_generalist  : AER, QJE, JPE, Econometrica, REStud
macro_monetario   : JME, JMCB y similares
econometria       : JBES, JOE, Econometric Theory
finanzas          : JF, RFS, JFE
internacional     : JIE y similares
otros_mainstream  : resto del mainstream
wp_banxico        : working papers Banco de Mexico (= autocitacion)
wp_multilateral   : IMF WP, World Bank WP, BIS
wp_bc_avanzado    : FED, ECB, BoE, BoC WPs
wp_bc_latam       : bancos centrales latinoamericanos
libro_mainstream  : libros de texto y monografias mainstream
heterodoxo        : JPKE, Cambridge JE, Review of Political Economy, etc.

---

## Hallazgos principales

1. 99.8% de referencias = mainstream ortodoxo
2. 0 citas a Minsky, Kalecki, Lavoie, Sraffa, JPKE, Cambridge JE (incluso post-2008)
3. 0 menciones en abstracts: Prebisch, CEPAL, dinero endogeno, MMT, conflict inflation
4. Quiebre 2001: vocabulario DSGE pasa de 0.9% a 15.9% con el inflation targeting
5. Autor mas citado: Ben Bernanke (37x)
6. Autocitacion creciente: 4% global -> 22% en periodo reciente
7. Vintage estable: mediana 9 anios, pero composicion por era cambia radicalmente
8. Ramos Francia = portador principal del toolkit NK (31 papers, nk_score 15)

---

## Posibles zonas de expansion

Corpus actual:
  - Full-text NLP sobre PDFs completos (no solo abstracts)
  - Citation network completa: referencias de todos los PDFs
  - Impacto externo: cuantas veces citan a autores DIBM en la literatura internacional
  - Evolucion intra-autoral: cambio de vocabulario de un autor a lo largo del tiempo

Comparacion con otros bancos centrales:
  - Fed, BoE, BIS, Banrep Colombia, Banco de Espania
  - Ubica al Banxico en el espacio bibliometrico regional

Background institucional:
  - Formacion doctoral de autores (institucion, advisor) via Google Scholar / CVs publicos
  - Probar hipotesis Babb: autores formados en EEUU usan mas vocabulario NK?

Nuevas tecnicas (requieren instalar paquetes):
  - BERTopic (sentence_transformers + hdbscan): topic modeling con transformers
  - UMAP: reduccion dimensional, preserva estructura global mejor que t-SNE
  - LDA: comparar topicos con NMF

---

## Como retomar el proyecto

El contexto vive en:
  ~/.claude/projects/.../memory/MEMORY.md

Se carga automaticamente al abrir Claude Code en el directorio del proyecto.

Para retomar en nueva sesion:
  1. Abrir Claude Code en C:/Users/USER/OneDrive/Escritorio/claudio/banxico-dibm/
  2. Iniciar con: Continuamos el proyecto DIBM Banxico. [describir tarea]

Repositorio:  https://github.com/sagmol/banxico-dibm
GitHub Pages: https://sagmol.github.io/banxico-dibm/

---

## Marco teorico

- Sarah Babb (Managing Mexico): formacion doctoral EEUU como vector de la ortodoxia
- Jacqueline Best: pensamiento interno de bancos centrales desde era Thatcher-Reagan
- Marc Lavoie: distincion mainstream/ortodoxo/heterodoxo
- Card & DellaVigna (2013): jerarquia Top-5 journals en economia
- Storm (2021): DSGE como membership card de la profesion
- Muellbauer (INET Edinburgh): Euler equation straitjacket

---

*Generado: marzo 2026 | Tesis doctoral*