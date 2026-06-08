# Fuentes de precios unitarios y APU de Bolivia

Investigación profunda (deep research, 5 frentes verificados) de fuentes para
alimentar el **Banco de APU** del programa (menú "Banco de APU" → subir
Formularios B-2 en Excel).

> El programa importa Formularios B-2 (.xlsx) sin consumir tokens. La estrategia
> es conseguir B-2 / presupuestos reales y subirlos al banco. Lo demás (catálogos
> online, normativa) sirve para calibrar precios y porcentajes.

Leyenda de confianza: **[OFICIAL]** gob.bo · **[CONFIRMADO]** fuente real
verificada · **[VERIFICAR]** existe pero requiere abrir manualmente.

---

## 1. Fuentes OFICIALES del Estado (descargables)

### SICOES — Sistema de Contrataciones Estatales  ⭐ (la más rica) [OFICIAL]
- https://www.sicoes.gob.bo/portal/index.php
- Publica los **DBC (Documento Base de Contratación)** de cada obra licitada:
  volúmenes de obra, presupuesto referencial y **formularios B-2 (APU) reales**.
  Incluye obras de ABC, municipios y AEVIVIENDA.
- Descargable por convocatoria (CUCE); algunas piden captcha.
- Vía práctica para conseguir APUs oficiales por obra y subirlos al banco.

### MEFP — Modelos de DBC de Obras (formularios oficiales) [OFICIAL]
El órgano rector es el Ministerio de Economía y Finanzas Públicas. Los formularios
B-1…B-5 y A-8/A-9 NO están en el cuerpo del DS 0181, sino en los Modelos de DBC:
- DBC Licitación Pública de Obras (02/02/2022):
  https://www.economiayfinanzas.gob.bo/sites/default/files/2023-01/DBC_LP_OBRAS_02022022.pdf
- DBC ANPE Obras:
  https://economiayfinanzas.gob.bo/sites/default/files/2023-01/DBC_ANPE_OBRAS_02022022.pdf
- DBC ANPE Obras (SIGEP 2025):
  https://portal.sigep.gob.bo/wp-content/uploads/2025/03/1132025DBCANPEOBRAS.pdf
- DS 0181 (NB-SABS) texto compilado:
  https://www.economiayfinanzas.gob.bo/index.php/node/9745  ·
  https://portal.sigep.gob.bo/wp-content/uploads/2018/07/COMPILADO-D.S.-0181-2017.pdf

### MOPSV — Guía Boliviana del APU (metodología) [OFICIAL]
- Guía Boliviana para la Elaboración del Análisis de Precios Unitarios, MOPSV,
  Resolución Ministerial 058 (01/02/2018). Define cargas sociales, herramientas,
  gastos generales, IT/IVA. Es la referencia para construir el B-2.
- Guías de diseño y de edificaciones:
  https://www.oopp.gob.bo/wp-content/uploads/2020/antiguos/Guia-Boliviana-para-diseno.pdf

### YPFB Contrataciones — Costos Unitarios Elementales [OFICIAL] [VERIFICAR]
- https://contrataciones.ypfb.gob.bo/comun/downloadFile/1071000000017253
- Tabla oficial de precios elementales (materiales/mano de obra/equipo). Abrir
  para confirmar formato (PDF/Excel).

### INE — Índice de Costo de la Construcción (ICC) [OFICIAL]
- https://icc.ine.gob.bo/
- Precios de materiales, servicios y mano de obra en La Paz, El Alto, Cochabamba
  y Santa Cruz. Útil para tendencia/variación de precios.

### AEVIVIENDA — SIMCO  ·  GAMLP — Precios Unitarios municipales [OFICIAL]
- https://simco.aevivienda.gob.bo/  (presupuestos de vivienda, PDF)
- https://lapaz.bo/presupuesto/  (Listado General de Precios Unitarios municipal)

> datos.gob.bo: **NO** existe dataset abierto de precios de construcción / APUs
> (confirmado negativo). Tampoco hay repositorios en GitHub con datos bolivianos.

---

## 2. Catálogos y bases de precios COMERCIALES

| Fuente | Qué ofrece | Acceso | Costo aprox. |
|---|---|---|---|
| **INSUCONS** | APU + materiales + mano de obra + equipo por ciudad, precios reales | Web pública (consulta, sin API) | Gratis consulta |
| **APUCONS** | Elaboración de presupuestos y APU online | Suscripción | ~USD 99/año (prueba 7 días) |
| **CYPE — Generador de precios Bolivia** | Banco de obra nueva, descompuesto; exporta **BC3/FIEBDC-3** | Consulta online gratis | Export/Arquímedes de pago |
| **PRESCOM** | Software de presupuestos y APU (escritorio) | Licencia | ~Bs 600 |
| **PresconIA** | SaaS, 25.000+ materiales, asistente IA | Suscripción | — |
| **Revista P&C / "Construir" (CADECOCRUZ)** | Tarifarios de materiales y mano de obra (Santa Cruz/Cbba/Tarija) | Revista/PDF | Suscripción |
| **Presupuestos Bolivia** | Plantilla Excel macro B-1/B-2/B-3 + base editable | Demo gratis / completo de pago | WhatsApp |

URLs: https://www.insucons.com/analisis-precio-unitario ·
https://www.apucons.com/bo/ · https://bolivia.generadordeprecios.info/ (y
https://bolivia.generadordeprecios.info/fiebdc/) ·
https://cadecocruz.org.bo/construir/construir25/Construir25.pdf ·
https://sites.google.com/view/presupuestosbolivia/inicio

> INSUCONS estructura sus APU por grupos en URLs predecibles (ej.
> .../hh/grupos/10/hormigones); no hay API — integrarlo sería scraping sujeto a
> sus términos. CYPE es la única con export a un estándar (BC3/FIEBDC-3).

---

## 3. Mano de obra y leyes sociales (para calibrar el APU)

Factores estándar del APU boliviano (Guía MOPSV RM 058/2018) — **CONFIRMADOS**:

| Concepto | Valor | Se aplica sobre |
|---|---|---|
| Cargas / beneficios sociales | **55% – 71,18%** | Subtotal de mano de obra |
| IVA mano de obra | **14,94%** | (Subtotal MO + cargas sociales) |
| Herramientas menores | **~5%** | Mano de obra total |
| Gastos generales | ~10% (referencial) | Costo directo (1+2+3) |
| Utilidad | ~10% (referencial) | Subtotal + GG |
| IT (Impuesto a las Transacciones) | **3,09%** | Total |

- 14,94% = 13/87 (IVA "por dentro"); 3,09% = 3/97 (IT "por dentro").
- El programa ya usa estos factores (editables en "PRESUPUESTO BOLIVIA con IA").

Jornales referenciales (InsuCons, base ~2022, **desactualizados** — verificar 2025):
ayudante/peón Bs 100/día · maestro albañil Bs 150/día · maestro plomero Bs 140/día ·
operador equipo pesado Bs 152–185/día. Mercado abierto: albañil Bs 100–180/día.

Cámaras: **CADECOCRUZ** (Santa Cruz, revista "Construir"), **CABOCO** (matriz
nacional), **CADECOCBBA** (Cochabamba) — todas usan la misma estructura de APU.

---

## 4. Formularios del DBC de Obras (qué genera el programa)

- **B-1** Presupuesto por Ítems y General de la Obra
- **B-2** Análisis de Precios Unitarios (un APU por ítem) ← formato que importa el banco
- **B-3** Precios Unitarios Elementales (sin recargos; idénticos a los del B-2)
- **B-4** Costo de Trabajo de los Equipos (costo horario)
- **B-5** Cronograma / costo de mano de obra (denominación varía por modelo)
- **A-8** Cronograma de Ejecución de la Obra
- **A-9** Cronograma de Movilización de Equipo

---

## Cómo usar estas fuentes con el programa
1. Descarga DBC/presupuestos desde **SICOES** (B-2 en Excel cuando esté) — es la
   fuente prioritaria de APUs oficiales reales.
2. Menú **"Banco de APU"** → "Cargar al banco" → sube los archivos.
3. El programa extrae materiales, mano de obra y equipo con sus precios y los usa
   como referencia prioritaria (similitud Jaccard) al generar nuevos APU.
4. Para precios de insumos puntuales, consulta INSUCONS / CYPE Bolivia / revista
   "Construir" y ajústalos en el editor de recursos.

### Formatos que importa el Banco de APU (sin consumir tokens)
- **Formulario B-2 (.xlsx)** — formato oficial boliviano (de SICOES, tesis, etc.).
- **BC3 / FIEBDC-3 (.bc3)** — estándar de intercambio de presupuestos. Es la vía
  para traer datos de **CYPE Generador de precios Bolivia** (exporta a BC3),
  Arquímedes o Presto. El importador reconstruye cada partida con su descomposición
  en materiales (mt), mano de obra (mo) y equipo (mq), con sus rendimientos y
  precios elementales. Implementado en `core/importador_bc3.py`.

> Pendiente: **YPFB "Costos Unitarios Elementales"** — requiere abrir el archivo
> real (`contrataciones.ypfb.gob.bo/.../1071000000017253`) para conocer su formato
> exacto y escribir su parser. No se pudo descargar durante la investigación.
