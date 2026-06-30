"""Página de Proveedores Bolivia: alta, edición, verificación, precios."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from models.supplier import TIPOS_PROVEEDOR, Proveedor
from providers import supplier_repository, supplier_service
from ui.components import requiere_proyecto


def render(proyecto):
    st.title(" Proveedores Bolivia")

    tab_lista, tab_alta, tab_precios = st.tabs(
        [" Lista", " Alta proveedor", " Precios de referencia"])

    # ---------------------------------------------------------------- lista
    with tab_lista:
        c1, c2 = st.columns(2)
        cat = c1.selectbox("Categoría", ["(todas)"] + TIPOS_PROVEEDOR)
        region = c2.text_input("Región")
        proveedores = supplier_repository.listar_proveedores(
            categoria=None if cat == "(todas)" else cat,
            region=region or None)
        if not proveedores:
            st.info("No hay proveedores registrados con esos filtros.")
        else:
            df = pd.DataFrame([{
                "id": p.id, "Nombre": p.nombre, "Categoría": p.categoria,
                "Email": p.email, "Teléfono": p.telefono, "Región": p.region,
                "Ciudad": p.ciudad, "Verificado": "" if p.verificado else "—",
                "Estado": p.estado, "Fuente": p.fuente_alta} for p in proveedores])
            st.dataframe(df, use_container_width=True, hide_index=True)

            col1, col2 = st.columns(2)
            pid = col1.number_input("ID proveedor", min_value=0, step=1)
            accion = col2.selectbox("Acción", ["Verificar", "Desactivar"])
            if st.button("Aplicar acción") and pid:
                if accion == "Verificar":
                    supplier_service.verificar(int(pid))
                else:
                    supplier_service.desactivar(int(pid))
                st.success("Acción aplicada.")
                st.rerun()

    # ----------------------------------------------------------------- alta
    with tab_alta:
        with st.form("alta_prov", clear_on_submit=True):
            c1, c2 = st.columns(2)
            nombre = c1.text_input("Nombre comercial *")
            razon = c2.text_input("Razón social")
            c3, c4, c5 = st.columns(3)
            nit = c3.text_input("NIT")
            email = c4.text_input("Email")
            telefono = c5.text_input("Teléfono / WhatsApp")
            c6, c7, c8 = st.columns(3)
            categoria = c6.selectbox("Categoría", TIPOS_PROVEEDOR)
            region = c7.text_input("Región / departamento")
            ciudad = c8.text_input("Ciudad")
            sitio = st.text_input("Sitio web")
            materiales = st.text_area("Materiales / servicios que ofrece", height=70)
            if st.form_submit_button("Guardar proveedor") and nombre:
                supplier_service.alta_manual(Proveedor(
                    nombre=nombre, razon_social=razon, nit=nit, email=email,
                    telefono=telefono, whatsapp=telefono, region=region,
                    ciudad=ciudad, sitio_web=sitio, categoria=categoria,
                    materiales_servicios=materiales))
                st.success(f"Proveedor '{nombre}' registrado.")
                st.rerun()

    # -------------------------------------------------------------- precios
    with tab_precios:
        st.caption("Precios de referencia internos (Nivel 1 del cotizador).")
        with st.form("alta_precio", clear_on_submit=True):
            c1, c2 = st.columns(2)
            desc = c1.text_input("Descripción del material *")
            categoria = c2.text_input("Categoría", "cemento")
            c3, c4, c5 = st.columns(3)
            unidad = c3.text_input("Unidad", "bolsa")
            precio = c4.number_input("Precio (BOB)", 0.0, step=1.0)
            region = c5.text_input("Región")
            prov_id = st.number_input("ID proveedor (opcional)", min_value=0, step=1)
            if st.form_submit_button("Registrar precio") and desc and precio > 0:
                supplier_repository.registrar_precio(
                    descripcion=desc, categoria=categoria, unidad=unidad,
                    precio=precio, region=region,
                    proveedor_id=int(prov_id) or None, fuente="bd")
                st.success("Precio registrado en la BD interna.")

        st.divider()
        st.markdown("**Carga masiva de precios (CSV / Excel)**")
        st.caption("Sube tu lista de precios reales. Columnas mínimas: "
                   "**descripcion**, **unidad**, **precio**. Opcionales: "
                   "categoria, region, moneda. Estos precios alimentan el "
                   "Nivel 1 del cotizador para que los APU salgan con precio.")
        archivo = st.file_uploader("Archivo de precios", type=["csv", "xlsx", "xls"],
                                   key="precios_masivo")
        if archivo is not None and st.button("Importar precios del archivo"):
            from core.importar_precios import importar_precios
            import tempfile
            from pathlib import Path
            try:
                suf = Path(archivo.name).suffix or ".csv"
                with tempfile.NamedTemporaryFile(delete=False, suffix=suf) as tmp:
                    tmp.write(archivo.getbuffer())
                    ruta_tmp = tmp.name
                with st.spinner("Importando precios..."):
                    res = importar_precios(ruta_tmp, fuente="importado")
                st.success(f"Importados {res['importados']} precios "
                           f"({res['omitidos']} omitidos de {res['total']}).")
                if res["errores"]:
                    st.warning("Algunas filas con error:\n" +
                               "\n".join(res["errores"][:10]))
            except Exception as exc:
                st.error(f"No se pudo importar: {exc}")
