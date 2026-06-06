#!/bin/sh
# Arranque seguro: corrige permisos del disco persistente y baja privilegios.
set -e

# El disco de Render se monta en runtime; asegura que exista y sea escribible
# por el usuario de la aplicacion (appuser).
mkdir -p /data

if [ "$(id -u)" = "0" ]; then
    # Estamos como root: ajustamos la propiedad del volumen montado y nos
    # reejecutamos como appuser (sin privilegios) con gosu.
    chown -R appuser:appuser /data 2>/dev/null || true
    exec gosu appuser "$0" "$@"
fi

# Ya como appuser (no-root): inicializa la BD y lanza la aplicacion.
python -m scripts.init_db
exec streamlit run app.py \
    --server.port=8501 \
    --server.address=0.0.0.0 \
    --server.headless=true
