# =============================================================================
#  APU Bolivia Generator — imagen Docker para despliegue en la nube
# =============================================================================
FROM python:3.11-slim

# Dependencias del sistema para OCR (Tesseract), lectura de PDF (Poppler) y
# gosu (para bajar privilegios de root a appuser en el arranque).
# Si no necesitas OCR en la nube, puedes quitar tesseract/poppler para una
# imagen más liviana.
RUN apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr tesseract-ocr-spa poppler-utils gosu \
    && rm -rf /var/lib/apt/lists/*

# Usuario sin privilegios para ejecutar la aplicación (no-root).
RUN useradd --create-home --uid 1000 appuser

WORKDIR /app

# Instalar dependencias primero (mejor caché de capas)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Nota: la verificacion de SEPREC usa la API oficial (no requiere navegador).
# Si activas SEPREC_USAR_NAVEGADOR como respaldo, descomenta la linea siguiente:
# RUN playwright install --with-deps chromium || true

# Copiar el código
COPY . .

# Carpeta de datos persistente (se monta como volumen en producción)
ENV APU_DB_PATH=/data/proveedores.db
RUN mkdir -p /data \
    && chmod +x /app/docker-entrypoint.sh \
    && chown -R appuser:appuser /app /data

# Inicializar el esquema de la base de datos al construir (idempotente en runtime)
EXPOSE 8501

# Healthcheck para plataformas que lo soporten
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1

# Arranque: el entrypoint corrige permisos del volumen, baja a usuario no-root
# (appuser) con gosu, inicializa la BD y lanza Streamlit.
ENTRYPOINT ["/app/docker-entrypoint.sh"]
