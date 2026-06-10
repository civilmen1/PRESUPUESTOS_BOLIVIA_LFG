"""Pruebas del importador de insucons (parser de tabla, sin red)."""
from __future__ import annotations

from scripts import importar_insucons as imp

# HTML de muestra que imita una pagina de APU (Descripcion/Unidad/Cantidad/
# Precio/Total con secciones MATERIALES / MANO DE OBRA / EQUIPO).
_HTML = """
<html><body>
<h1>Hormigon armado para columnas</h1>
<p>Unidad: m3 &mdash; Rendimiento referencial</p>
<table>
 <tr><th>Descripcion</th><th>Unidad</th><th>Cantidad</th>
     <th>Precio</th><th>Total</th></tr>
 <tr><td colspan="5">1. MATERIALES</td></tr>
 <tr><td>Cemento portland IP-30</td><td>kg</td><td>350,00</td>
     <td>1,20</td><td>420,00</td></tr>
 <tr><td>Arena comun</td><td>m3</td><td>0,55</td><td>120,00</td><td>66,00</td></tr>
 <tr><td>Subtotal Materiales</td><td></td><td></td><td></td><td>486,00</td></tr>
 <tr><td colspan="5">2. MANO DE OBRA</td></tr>
 <tr><td>Maestro albanil</td><td>hr</td><td>8,00</td><td>18,75</td><td>150,00</td></tr>
 <tr><td>Peon</td><td>hr</td><td>16,00</td><td>12,50</td><td>200,00</td></tr>
 <tr><td colspan="5">3. EQUIPO Y HERRAMIENTAS</td></tr>
 <tr><td>Mezcladora de hormigon</td><td>hr</td><td>4,00</td><td>25,00</td><td>100,00</td></tr>
 <tr><td>Herramientas menores (5%)</td><td>%</td><td>5,00</td><td></td><td>17,50</td></tr>
 <tr><td>TOTAL COSTO DIRECTO</td><td></td><td></td><td></td><td>1059,50</td></tr>
</table>
</body></html>
"""


def test_parsear_apu_separa_secciones_y_descarta_precios():
    apu = imp.parsear_apu(_HTML, url="http://x/apu/1")
    assert apu is not None
    assert "hormigon" in apu["actividad"].lower()
    assert apu["unidad"] == "m3"
    assert apu["fuente"] == "Insucons"

    # Materiales: cemento y arena (NO el subtotal).
    desc_mat = [m["descripcion"] for m in apu["materiales"]]
    assert any("cemento" in d.lower() for d in desc_mat)
    assert any("arena" in d.lower() for d in desc_mat)
    assert not any("subtotal" in d.lower() for d in desc_mat)

    # Rendimientos conservados, precios SIEMPRE en 0.
    cemento = next(m for m in apu["materiales"] if "cemento" in m["descripcion"].lower())
    assert cemento["cantidad"] == 350.0
    assert all(m["precio"] == 0 for m in apu["materiales"])

    # Mano de obra: 2 obreros, en horas, 'peon' normalizado a no-peon.
    assert len(apu["mano_obra"]) == 2
    assert all(r["unidad"] == "HR" and r["precio"] == 0 for r in apu["mano_obra"])
    assert not any("peon" in r["descripcion"].lower() for r in apu["mano_obra"])

    # Equipo: la mezcladora si; 'herramientas menores (5%)' se descarta por '%'.
    desc_eq = [e["descripcion"].lower() for e in apu["equipo"]]
    assert any("mezcladora" in d for d in desc_eq)
    assert not any("herramientas menores" in d for d in desc_eq)


def test_descubrir_enlaces_filtra_grupos():
    html = """
    <a href="/analisis-precio-unitario/hh/grupos">Grupos</a>
    <a href="/analisis-precio-unitario/hh/item/123">APU 123</a>
    <a href="https://www.insucons.com/analisis-precio-unitario/hh/item/456">APU 456</a>
    <a href="/otra-cosa">Ruido</a>
    """
    enlaces = imp._descubrir_enlaces(html, "https://www.insucons.com/x")
    assert any("item/123" in e for e in enlaces)
    assert any("item/456" in e for e in enlaces)
    assert not any(e.rstrip("/").endswith("grupos") for e in enlaces)
    assert not any("otra-cosa" in e for e in enlaces)
