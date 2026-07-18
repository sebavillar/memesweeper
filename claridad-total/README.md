# Claridad Total

Plataforma inmobiliaria nativa en IA que elimina la intermediación opaca y da información
simétrica y verificada a comprador y vendedor. Mercado inicial: **Gran Mendoza, Argentina**.

## Contenido de esta carpeta

### Informes (HTML, abrir en el navegador)
- **`informes/01-informe-estrategico.html`** — Investigación global y diseño de producto: por qué
  el real estate no es un commodity (asimetría de información / "mercado de limones"), anatomía del
  intermediario, 10 casos de éxito y fracaso en el mundo (Zillow, Opendoor, Purplebricks, QuintoAndar,
  Habi, tokenización, IA agéntica), patrones destilados, arquitectura de producto, modelo de negocio,
  puntos de mejora, riesgos y roadmap.
- **`informes/02-plan-mendoza.html`** — Plan de arranque en Mendoza. Las dos restricciones
  (comercialización y datos) resueltas con la misma jugada: el corredor matriculado como núcleo legal
  y llave de acceso al dato del Registro. Fuentes de datos locales (ATM/Catastro, IDE, Registro de la
  Propiedad Raíz), estrategia cold-start del dataset, MVP "Pasaporte del inmueble", roadmap 0→1.
- **`informes/03-spec-tecnica-mvp.html`** — Especificación técnica del MVP: arquitectura en 4 capas,
  pipeline de datos, motor de valuación explicable (heurístico → hedónico/ML), capa de IA (RAG + tool
  use), stack propuesto (FastAPI, PostgreSQL+PostGIS, Playwright, Next.js, API Claude) y plan a 12 semanas.

### Prototipo funcional
- **`prototipo/pasaporte-demo.html`** — Prototipo interactivo del "Pasaporte del Inmueble" con un motor
  de valuación explicable real (corre en el navegador, sin backend). Datos de muestra realistas de
  Mendoza 2025. Permite elegir casos o ajustar atributos y ver la valuación desglosada factor por factor,
  el rango de confianza, comparables y el estado dominial con banderas rojas.

### PDF
- `pdf/` — Versiones descargables de los tres informes.

## Idea en una frase

No es un portal de avisos ni un iBuyer: es la **capa de confianza e información simétrica verificada**
que el mercado inmobiliario nunca tuvo, con la IA haciendo el trabajo que antes justificaba una comisión
del 3–6%.

## Estado

Fase de definición de producto. Próximo hito en desarrollo: **agente de WhatsApp** que responde consultas
de compradores sobre el inventario propio (ver plan de desarrollo aparte).
