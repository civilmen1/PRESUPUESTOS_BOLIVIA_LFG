"""Portal del PROVEEDOR: ver solicitudes de cotización y responder precios.

Dirigido al segundo público del sistema: proveedores de materiales que reciben
solicitudes de cotización y registran sus precios, plazos y disponibilidad.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from core import currency
from providers import email_service


def render(usuario=None):
    st.title(" Portal del Proveedor — Cotizaciones")
    st.caption("Recibe solicitudes de cotización y registra tus precios para "
               "integrar la base de precios de materiales más grande de Bolivia.")

    proveedor_id = getattr(usuario, "proveedor_id", None) if usuario else None
    if not proveedor_id:
        st.warning("Tu cuenta no está vinculada a un proveedor. Contacta al "
                   "administrador.")
        return

    solicitudes = email_service.solicitudes_de_proveedor(proveedor_id)
    pendientes = [s for s in solicitudes if not s.get("respondio")]
    st.metric("Solicitudes recibidas", len(solicitudes),
              f"{len(pendientes)} pendientes")

    if not solicitudes:
        st.info("No tienes solicitudes de cotización todavía.")
    for s in solicitudes:
        estado = " respondida" if s.get("respondio") else "⏳ pendiente"
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
                disp = st.text_input("Disponibilidad / stock", key=f"di_{s['id']}")
                obs = st.text_input("Observaciones", key=f"o_{s['id']}")
                if st.form_submit_button(" Enviar cotización") and desc and precio > 0:
                    email_service.guardar_respuesta_cotizacion(
                        contacto_id=s["id"], proveedor_id=proveedor_id,
                        descripcion=desc, unidad=unidad, precio=precio,
                        moneda=moneda, plazo_entrega=plazo,
                        disponibilidad=disp, vigencia_dias=int(vig),
                        observaciones=obs)
                    st.success("¡Cotización registrada! Gracias.")
                    st.rerun()

    st.divider()
    st.subheader(" Mis cotizaciones enviadas")
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
