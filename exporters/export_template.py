"""Generación de la plantilla Excel de tabla de cantidades para descargar.

La plantilla usa los encabezados típicos de tablas de cantidades bolivianas
e incluye filas de ejemplo, incluyendo **filas de título de módulo** (sin
unidad ni cantidad) que el parser detecta automáticamente.
"""
from __future__ import annotations

import io
from pathlib import Path

import pandas as pd

# Encabezados de la plantilla (compatibles con el detector de columnas)
COLUMNAS = ["N°", "CODIGO ESPECIFICACION", "ITEM", "UND", "CANTIDAD",
            "OBSERVACIONES"]

# Filas de ejemplo. Las filas SIN número/unidad/cantidad son TÍTULOS DE MÓDULO.
FILAS_EJEMPLO = [
    ["", "", "MÓDULO 1: OBRAS PRELIMINARES", "", "", "← fila de título de módulo"],
    ["1", "OP-01", "Replanteo y trazado de la obra", "m2", 250, ""],
    ["2", "OP-02", "Excavación manual para cimientos", "m3", 45, "Terreno semiduro"],
    ["", "", "MÓDULO 2: OBRA GRUESA", "", "", "← fila de título de módulo"],
    ["3", "OG-01", "Hormigón armado para zapatas H21", "m3", 18.5, "Incluye encofrado"],
    ["4", "OG-02", "Muro de mampostería de ladrillo gambote", "m2", 220, "Espesor 18cm"],
    ["", "", "MÓDULO 3: INSTALACIONES", "", "", "← fila de título de módulo"],
    ["5", "IN-01", "Provisión y tendido de tubería PVC 4''", "ml", 85, ""],
    ["", "", "MÓDULO 4: ACABADOS", "", "", "← fila de título de módulo"],
    ["6", "AC-01", "Pintura látex en muros interiores", "m2", 340, "Dos manos"],
    ["7", "AC-02", "Revestimiento cerámico de pisos", "m2", 160, "Cerámica 30x30"],
]


def _dataframe() -> pd.DataFrame:
    return pd.DataFrame(FILAS_EJEMPLO, columns=COLUMNAS)


def plantilla_bytes() -> bytes:
    """Devuelve el .xlsx de la plantilla como bytes (para descarga en la UI)."""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        _dataframe().to_excel(writer, sheet_name="Tabla de cantidades", index=False)
        instrucciones = pd.DataFrame({
            "INSTRUCCIONES": [
                "1. No cambies los nombres de las columnas de la primera hoja.",
                "2. Columna ITEM = descripción del trabajo (obligatoria).",
                "3. Una fila con texto en ITEM pero SIN UND ni CANTIDAD se toma "
                "como TÍTULO DE MÓDULO y agrupa a los ítems que vienen debajo.",
                "4. UND: unidad (m2, m3, ml, kg, pza, glb, etc.).",
                "5. CANTIDAD: número (usa punto o coma decimal).",
                "6. CODIGO ESPECIFICACION y OBSERVACIONES son opcionales.",
                "7. Borra estas filas de ejemplo antes de cargar tus datos.",
            ]
        })
        instrucciones.to_excel(writer, sheet_name="Instrucciones", index=False)
    return buffer.getvalue()


def guardar_plantilla(ruta: str | Path) -> Path:
    """Guarda la plantilla en disco y devuelve la ruta."""
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_bytes(plantilla_bytes())
    return ruta


if __name__ == "__main__":
    from config import settings

    salida = guardar_plantilla(settings.DATA_DIR / "plantilla_tabla_cantidades.xlsx")
    print(f"Plantilla generada en: {salida}")
