# Fuentes de precios unitarios y APU de Bolivia

Investigación de fuentes para alimentar el **Banco de APU** del programa
(menú "Banco de APU" → subir Formularios B-2 en Excel).

> El programa importa Formularios B-2 (.xlsx) sin consumir tokens. La estrategia
> es conseguir B-2 / presupuestos reales y subirlos al banco.

## Fuentes OFICIALES confirmadas (descargables)

### SICOES — Sistema de Contrataciones Estatales  ⭐ (la más rica)
- https://www.sicoes.gob.bo/portal/index.php
- Publica los **DBC (Documento Base de Contratación)** de cada obra licitada
  del Estado, con **volúmenes de obra, presupuesto referencial y formularios
  B-2 (APU)** reales. Incluye obras de ABC, municipios y AEVIVIENDA.
- Descargable por convocatoria (CUCE); algunas piden captcha. ~80/día.
- Es la vía práctica para conseguir APUs oficiales por obra y subirlos al banco.

### MOPSV — Ministerio de Obras Públicas (metodología APU)
- Guía Boliviana para Diseño y Presentación de Proyectos:
  https://www.oopp.gob.bo/wp-content/uploads/2020/antiguos/Guia-Boliviana-para-diseno.pdf
- Guía Boliviana de Construcción de Edificaciones:
  https://www.oopp.gob.bo/wp-content/uploads/2020/antiguos/Gu%C3%ADa_Boliviana_de_construcci%C3%B3n_de_edificaciones.pdf
- Marco metodológico del APU (no es tarifario actualizado).

### INE — Índice de Costo de la Construcción (ICC)
- https://icc.ine.gob.bo/  ·  https://www.ine.gob.bo/index.php/estadisticas-economicas/construccion/indice-de-costo-de-la-construccio/
- Precios de materiales, servicios y mano de obra en La Paz, El Alto,
  Cochabamba y Santa Cruz. Útil para tendencia/variación de precios.

### AEVIVIENDA — SIMCO (presupuestos de vivienda)
- https://simco.aevivienda.gob.bo/
- Especificaciones y contratos de obra con precios referenciales (PDF).

### GAMLP — Gobierno Municipal de La Paz
- https://lapaz.bo/  ·  https://lapaz.bo/presupuesto/
- "Listado General de Precios Unitarios" municipal (referencial).

## Cómo usar estas fuentes con el programa
1. Descarga DBC/presupuestos desde SICOES (formato B-2 en Excel cuando esté).
2. Menú "Banco de APU" → "Cargar al banco" → sube los .xlsx.
3. El programa extrae materiales, mano de obra y equipo con sus precios y los
   usa como referencia prioritaria al generar nuevos APU.

> Nota: portales privados (INSUCONS, PRESUPLAN, CYPE generadordeprecios,
> infosicoes) ofrecen datos pero NO son oficiales y suelen requerir suscripción.
