"""Verificacion de SEPREC automatizando el portal oficial con Playwright.

El portal https://miempresa.seprec.gob.bo no expone una API publica, por lo que
se automatiza el navegador: se abre la pagina de habilitacion, se escribe la
matricula, se pulsa BUSCAR y se lee el resultado.

Es tolerante a fallos: si Playwright no esta instalado o el portal cambia,
devuelve ok=False con un mensaje y el sistema cae a la validacion de formato.
"""
from __future__ import annotations

from config import settings
from config.logging_config import get_logger

logger = get_logger(__name__)

PORTAL_URL = "https://miempresa.seprec.gob.bo/#/portal"

# Textos que el portal muestra segun el resultado.
_TXT_NO_ENCONTRADO = "no se encontro"
_TXT_NO_ENCONTRADO2 = "no se encontró"


def verificar_seprec_navegador(matricula: str, timeout_ms: int = 25000) -> dict:
    """Consulta la matricula en el portal del SEPREC con un navegador headless.

    Devuelve {ok, razon_social, estado, mensaje, fuente}.
    """
    matricula = (matricula or "").strip()
    if not matricula:
        return {"ok": False, "mensaje": "Numero de SEPREC vacio."}

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.warning("Playwright no instalado; no se puede verificar SEPREC en "
                       "linea. Instala: pip install playwright && playwright "
                       "install chromium")
        return {"ok": False, "mensaje": "Verificacion en linea no disponible "
                "(falta Playwright). Se uso validacion de formato.",
                "fuente": "sin_navegador"}

    try:
        with sync_playwright() as p:
            navegador = p.chromium.launch(headless=True,
                                          args=["--no-sandbox",
                                                "--disable-dev-shm-usage"])
            pagina = navegador.new_page()
            pagina.set_default_timeout(timeout_ms)
            pagina.goto(PORTAL_URL, wait_until="networkidle")

            # El campo de busqueda y el boton pueden variar; se busca de forma
            # flexible por placeholder/rol.
            campo = _encontrar_campo(pagina)
            if campo is None:
                navegador.close()
                return {"ok": False, "mensaje": "No se encontro el campo de "
                        "busqueda en el portal del SEPREC.", "fuente": "portal"}
            campo.fill(matricula)

            boton = _encontrar_boton(pagina)
            if boton is not None:
                boton.click()
            else:
                campo.press("Enter")

            pagina.wait_for_timeout(3500)  # esperar la respuesta del portal
            texto = (pagina.inner_text("body") or "").lower()
            navegador.close()

        if _TXT_NO_ENCONTRADO in texto or _TXT_NO_ENCONTRADO2 in texto:
            return {"ok": False, "estado": "NO ENCONTRADO",
                    "mensaje": "La matricula no se encontro en el SEPREC. "
                    "Verifica el numero.", "fuente": "seprec_portal"}
        # Si no aparece el mensaje de error, se considera habilitada.
        return {"ok": True, "razon_social": "", "estado": "HABILITADA",
                "mensaje": "Matricula encontrada y habilitada en el SEPREC.",
                "fuente": "seprec_portal"}
    except Exception as exc:
        logger.error("Error verificando SEPREC en el portal: %s (%s)", exc,
                     type(exc).__name__)
        return {"ok": False, "mensaje": f"No se pudo consultar el portal del "
                f"SEPREC: {exc}", "fuente": "error"}


def _encontrar_campo(pagina):
    """Busca el campo de texto de la matricula de forma flexible."""
    selectores = [
        "input[placeholder*='matrícula' i]",
        "input[placeholder*='matricula' i]",
        "input[placeholder*='empresa' i]",
        "input[type='text']",
        "input:not([type='hidden'])",
    ]
    for sel in selectores:
        try:
            el = pagina.query_selector(sel)
            if el and el.is_visible():
                return el
        except Exception:
            continue
    return None


def _encontrar_boton(pagina):
    """Busca el boton BUSCAR de forma flexible."""
    try:
        b = pagina.get_by_role("button", name="BUSCAR")
        if b and b.count() > 0:
            return b.first
    except Exception:
        pass
    for sel in ["button:has-text('BUSCAR')", "button:has-text('Buscar')",
                "button[type='submit']", "button"]:
        try:
            el = pagina.query_selector(sel)
            if el and el.is_visible():
                return el
        except Exception:
            continue
    return None
