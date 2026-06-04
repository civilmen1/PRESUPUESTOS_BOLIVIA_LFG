# =============================================================================
#  APU Bolivia Generator — imagen Docker para despliegue en la nube
# =============================================================================
FROM python:3.11-slim

# Dependencias del sistema para OCR (Tesseract) y lectura de PDF (Poppler).
# Si no necesitas OCR en la nube, puedes quitar tesseract/poppler para una
# imagen más liviana.
RUN apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr tesseract-ocr-spa poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instalar dependencias primero (mejor caché de capas)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Navegador para la verificación de SEPREC (Playwright + Chromium y sus libs).
# Si no usarás verificación de SEPREC por navegador, puedes quitar esta línea
# para una imagen más liviana.
RUN playwright install --with-deps chromium || true

# Copiar el código
COPY . .

# Carpeta de datos persistente (se monta como volumen en producción)
ENV APU_DB_PATH=/data/proveedores.db
RUN mkdir -p /data

# Inicializar el esquema de la base de datos al construir (idempotente en runtime)
EXPOSE 8501

# Healthcheck para plataformas que lo soporten
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1

# Arranque: inicializa la BD y lanza Streamlit
CMD ["sh", "-c", "python -m scripts.init_db && streamlit run app.py --server.port=8501 --server.address=0.0.0.0 --server.headless=true"]
