"""Lectura y validación de casos de prueba en formato JSON.

Este es el ÚNICO módulo que conoce el formato de archivo. Si los casos de la
profesora llegan en otro formato, basta con adaptar `caso_desde_dict` (o
agregar un lector nuevo) sin tocar la lógica de los algoritmos.

Formato aceptado (ver README para ejemplos completos):

{
  "id": "caso_01",
  "aceleracion": {
    "presupuesto": 6,
    "etapas": [ {"t": 5, "c": 3, "d": 2}, [8, 4, 5], ... ]
  },
  "auditoria": {
    "categorias": 5                      # o una lista de nombres ["sesgo", ...]
    "interacciones": [ [1, 2, 3], {"id": "I2", "cubre": [3, 4]}, ... ]
  }
}

Cualquiera de las dos partes puede omitirse.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .modelos import Caso, Etapa, InstanciaAceleracion, InstanciaAuditoria


class ErrorDeFormato(ValueError):
    """El caso no cumple el formato o las condiciones de la formalización."""


def _entero(valor: Any, campo: str) -> int:
    if isinstance(valor, bool):
        raise ErrorDeFormato(f"{campo} debe ser un entero, se recibió {valor!r}")
    if isinstance(valor, int):
        return valor
    if isinstance(valor, float) and valor.is_integer():
        return int(valor)
    raise ErrorDeFormato(f"{campo} debe ser un entero, se recibió {valor!r}")


def _numero(valor: Any, campo: str) -> float:
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise ErrorDeFormato(f"{campo} debe ser numérico, se recibió {valor!r}")
    return valor


def _lista(valor: Any, campo: str) -> list:
    if not isinstance(valor, list):
        raise ErrorDeFormato(f"{campo} debe ser una lista, se recibió {valor!r}")
    return valor


def _leer_aceleracion(datos: dict) -> InstanciaAceleracion:
    if not isinstance(datos, dict):
        raise ErrorDeFormato("'aceleracion' debe ser un objeto JSON")
    if "presupuesto" not in datos or "etapas" not in datos:
        raise ErrorDeFormato("'aceleracion' debe tener 'presupuesto' y 'etapas'")
    B = _entero(datos["presupuesto"], "presupuesto")
    if B < 0:
        raise ErrorDeFormato(f"el presupuesto debe ser >= 0, se recibió {B}")
    _lista(datos["etapas"], "etapas")
    etapas: list[Etapa] = []
    for i, e in enumerate(datos["etapas"], start=1):
        if isinstance(e, dict):
            t, c, d, nombre = e.get("t"), e.get("c"), e.get("d"), str(e.get("nombre", ""))
        elif isinstance(e, (list, tuple)) and len(e) == 3:
            (t, c, d), nombre = e, ""
        else:
            raise ErrorDeFormato(f"etapa {i}: use {{'t','c','d'}} o [t, c, d]")
        t = _numero(t, f"etapa {i}: t")
        c = _entero(c, f"etapa {i}: c")
        d = _numero(d, f"etapa {i}: d")
        if c < 0:
            raise ErrorDeFormato(f"etapa {i}: el costo c debe ser >= 0")
        if not (0 <= d <= t):
            raise ErrorDeFormato(f"etapa {i}: se exige 0 <= d <= t (d={d}, t={t})")
        etapas.append(Etapa(t=t, c=c, d=d, nombre=nombre))
    return InstanciaAceleracion(etapas=etapas, presupuesto=B)


def _leer_auditoria(datos: dict) -> InstanciaAuditoria:
    if not isinstance(datos, dict):
        raise ErrorDeFormato("'auditoria' debe ser un objeto JSON")
    if "categorias" not in datos or "interacciones" not in datos:
        raise ErrorDeFormato("'auditoria' debe tener 'categorias' e 'interacciones'")
    _lista(datos["interacciones"], "interacciones")
    cats = datos["categorias"]
    if isinstance(cats, list):
        nombres = [str(x) for x in cats]
        if len(set(nombres)) != len(nombres):
            raise ErrorDeFormato("hay nombres de categorías repetidos")
        indice = {nombre: k for k, nombre in enumerate(nombres)}
    else:
        r = _entero(cats, "categorias")
        if r < 0:
            raise ErrorDeFormato("el número de categorías debe ser >= 0")
        nombres = [str(k + 1) for k in range(r)]
        indice = {}

    def a_indice(x: Any, j: int) -> int:
        if indice:  # categorías con nombre
            clave = str(x)
            if clave not in indice:
                raise ErrorDeFormato(f"interacción {j}: categoría desconocida {x!r}")
            return indice[clave]
        k = _entero(x, f"interacción {j}: categoría")
        if not 1 <= k <= len(nombres):
            raise ErrorDeFormato(f"interacción {j}: categoría {k} fuera de 1..{len(nombres)}")
        return k - 1

    conjuntos: list[frozenset[int]] = []
    nombres_int: list[str] = []
    for j, s in enumerate(datos["interacciones"], start=1):
        if isinstance(s, dict):
            nombres_int.append(str(s.get("id", j)))
            elementos = s.get("cubre", [])
        else:
            nombres_int.append(str(j))
            elementos = s
        if not isinstance(elementos, list):
            raise ErrorDeFormato(f"interacción {j}: la cobertura debe ser una lista")
        conjuntos.append(frozenset(a_indice(x, j) for x in elementos))
    return InstanciaAuditoria(categorias=nombres, interacciones=conjuntos,
                              nombres_interacciones=nombres_int)


def caso_desde_dict(datos: dict, origen: str = "") -> Caso:
    if not isinstance(datos, dict):
        raise ErrorDeFormato("el caso debe ser un objeto JSON")
    if "aceleracion" not in datos and "auditoria" not in datos:
        raise ErrorDeFormato("el caso no tiene 'aceleracion' ni 'auditoria'")
    caso_id = str(datos.get("id") or Path(origen).stem or "caso")
    acel = _leer_aceleracion(datos["aceleracion"]) if datos.get("aceleracion") else None
    aud = _leer_auditoria(datos["auditoria"]) if datos.get("auditoria") else None
    return Caso(id=caso_id, aceleracion=acel, auditoria=aud, origen=origen)


def cargar_caso(ruta: str | Path) -> Caso:
    ruta = Path(ruta)
    try:
        # utf-8-sig acepta archivos con BOM (p. ej. guardados con el Bloc de notas)
        datos = json.loads(ruta.read_text(encoding="utf-8-sig"))
    except UnicodeDecodeError as e:
        raise ErrorDeFormato(f"el archivo no está en UTF-8: {e}") from e
    except json.JSONDecodeError as e:
        raise ErrorDeFormato(f"JSON inválido: {e}") from e
    return caso_desde_dict(datos, origen=str(ruta))


def listar_casos(rutas: list[str | Path]) -> list[Path]:
    """Expande carpetas a sus archivos .json (en orden alfabético)."""
    archivos: list[Path] = []
    for r in rutas:
        p = Path(r)
        if p.is_dir():
            archivos.extend(sorted(p.glob("*.json")))
        else:
            archivos.append(p)
    return archivos
