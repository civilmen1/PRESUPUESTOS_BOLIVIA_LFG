"""Portal del PROVEEDOR: ver solicitudes de cotización y responder precios.

Dirigido al segundo público del sistema: proveedores de materiales que reciben
solicitudes de cotización y registran sus precios, plazos y disponibilidad.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from core import currency
from providers import email_service, supplier_repository, supplier_service
from models.supplier import TIPOS_PROVEEDOR, Proveedor


def render():
    st.title("🏭 Portal del Proveedor — Cotizaciones")
    st.caption("Recibe solicitudes de cotización y registra tus precios para "
               "integrar la base de precios de materiales más grande de Bolivia.")

    proveedores = supplier_repository.listar_proveedores()
    tab_sel, tab_registro = st.tabs(["🔎 Soy proveedor registrado",
                                     "➕ Registrarme como proveedor"])

    # ------------------------------------------------------------ registro
    with tab_registro:
        with st.form("registro_proveedor", clear_on_submit=True):
            st.markdown("**Datos de la empresa proveedora**")
            c1, c2 = st.columns(2)
            nombre = c1.text_input("Nombre comercial *")
            razon = c2.text_input("Razón social")
            c3, c4, c5 = st.columns(3)
            nit = c3.text_input("NIT")
            email = c4.text_input("Email *")
            telefono = c5.text_input("Teléfono / WhatsApp")
            c6, c7, c8 = st.columns(3)
            categoria = c6.selectbox("Rubro", TIPOS_PROVEEDOR)
            region = c7.text_input("Departamento")
            ciudad = c8.text_input("Ciudad")
            materiales = st.text_area("Materiales / servicios que ofrece")
            if st.form_submit_button("Registrarme", type="primary") and nombre and email:
                supplier_service.alta_manual(Proveedor(
                    nombre=nombre, razon_social=razon, nit=nit, email=email,
                    telefono=telefono, whatsapp=telefono, region=region,
                    ciudad=ciudad, categoria=categoria,
                    materiales_servicios=materiales))
                st.success(f"¡Gracias {nombre}! Quedaste registrado. Ahora puedes "
                           "ver tus solicitudes en la otra pestaña.")

    # --------------------------------------------------------- solicitudes
    with tab_sel:
        if not proveedores:
            st.info("Aún no hay proveedores registrados. Regístrate en la otra "
                    "pestaña.")
            return
        opciones = {f"{p.id} · {p.nombre}": p.id for p in proveedores}
        clave = st.selectbox("Selecciona tu empresa", list(opciones.keys()))
        proveedor_id = opciones[clave]

        solicitudes = email_service.solicitudes_de_proveedor(proveedor_id)
        pendientes = [s for s in solicitudes if not s.get("respondio")]
        st.metric("Solicitudes recibidas", len(solicitudes),
                  f"{len(pendientes)} pendientes")

        if not solicitudes:
            st.info("No tienes solicitudes de cotización todavía.")
        for s in solicitudes:
            estado = "✅ respondida" if s.get("respondio") else "⏳ pendiente"
            with st.expander(f"{estado} · {s.get('asunto')} · "
                             f"{s.get('fecha_envio', '')[:10]}"):
                st.markdown(s.get("cuerpo") or "", unsafe_allow_html=True)
                st.divider()
                st.markdown("**Registrar mi cotización**")
                with st.form(f"cot_{s['id']}", clear_on_submit=True):
                    d1, d2, d3 = st.columns(3)
                    desc = d1.text_input("Material / recurso", key=f"d_{s['id']}")
                    unidad = d2.text_input("Unidad", key=f"u_{s['id']}")
                    moneda = d3.selectbox("Moneda", currency.codigos(),
                                          format_func=currency.etiqueta,
                                          key=f"m_{s['id']}")
                    e1, e2, e3 = st.columns(3)
                    precio = e1.number_input("Precio unitario", 0.0, step=1.0,
                                             key=f"p_{s['id']}")
                    plazo = e2.text_input("Plazo de entrega", key=f"pl_{s['id']}")
                    vig = e3.number_input("Vigencia (días)", 1, 365, 30,
                                          key=f"v_{s['id']}")
                    disp = st.text_input("Disponibilidad / stock",
                                         key=f"di_{s['id']}")
                    obs = st.text_input("Observaciones", key=f"o_{s['id']}")
                    if st.form_submit_button("📨 Enviar cotización") and desc and precio > 0:
                        email_service.guardar_respuesta_cotizacion(
                            contacto_id=s["id"], proveedor_id=proveedor_id,
                            descripcion=desc, unidad=unidad, precio=precio,
                            moneda=moneda, plazo_entrega=plazo,
                            disponibilidad=disp, vigencia_dias=int(vig),
                            observaciones=obs)
                        st.success("¡Cotización registrada! Gracias.")
                        st.rerun()

        st.divider()
        st.subheader("📋 Mis cotizaciones enviadas")
        respuestas = email_service.respuestas_de_proveedor(proveedor_id)
        if respuestas:
            df = pd.DataFrame([{
                "Material": r["descripcion"], "Unidad": r["unidad"],
                "Precio": r["precio"], "Moneda": r["moneda"],
                "Plazo": r["plazo_entrega"], "Vigencia (días)": r["vigencia_dias"],
                "Fecha": (r["fecha_respuesta"] or "")[:10]} for r in respuestas])
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.caption("Aún no has enviado cotizaciones.")
