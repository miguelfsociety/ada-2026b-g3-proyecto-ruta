"""Parte 2 — Cobertura mínima de auditoría (Set Cover).

- `verificar_factibilidad`: comprueba que la unión de todas las interacciones
  cubre las r categorías, en O(n·r).
- `voraz`: en cada paso elige la interacción que cubre más categorías aún no
  cubiertas (empates: la de menor índice). Hace a lo sumo min(n, r) elecciones
  y cada una revisa las n interacciones: O(n·r·min(n, r)). Garantía clásica:
  usa a lo sumo H(d) veces el óptimo, con d = máx |S_j| y H(d) <= H_r
  (Johnson, 1974; Chvátal, 1979).
- `exacta`: óptimo por fuerza bruta (subconjuntos por tamaño creciente), solo
  para instancias pequeñas; sirve para verificar la garantía del voraz.

Los conjuntos se representan como máscaras de bits (enteros de Python): el bit
k vale 1 si la interacción cubre la categoría k.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations

from .modelos import InstanciaAuditoria

MAX_N_EXACTA = 20


class AuditoriaInfactible(ValueError):
    pass


def _mascaras(inst: InstanciaAuditoria) -> list[int]:
    return [sum(1 << k for k in s) for s in inst.interacciones]


def _nombres_categorias(inst: InstanciaAuditoria, mascara: int) -> list[str]:
    return [inst.categorias[k] for k in range(inst.r) if mascara >> k & 1]


def armonico(d: int) -> float:
    return sum(1.0 / k for k in range(1, d + 1))


def verificar_factibilidad(inst: InstanciaAuditoria) -> tuple[bool, list[str]]:
    """Devuelve (factible, categorías que ninguna interacción cubre)."""
    union = 0
    for m in _mascaras(inst):
        union |= m
    universo = (1 << inst.r) - 1
    faltan = universo & ~union
    return faltan == 0, _nombres_categorias(inst, faltan)


def cubre_todo(inst: InstanciaAuditoria, seleccion: list[int]) -> bool:
    """`seleccion` usa índices desde 0."""
    m = _mascaras(inst)
    union = 0
    for j in seleccion:
        union |= m[j]
    return union == (1 << inst.r) - 1


@dataclass
class ResultadoAuditoria:
    seleccion: list[str]                  # nombres (o índices desde 1) de las interacciones
    tamano: int
    d: int
    cota_H_d: float
    traza: dict = field(default_factory=dict)

    def como_dict(self) -> dict:
        return {
            "interacciones_auditadas": self.seleccion,
            "numero_de_auditorias": self.tamano,
            "d_max_categorias_por_interaccion": self.d,
            "cota_H_d": round(self.cota_H_d, 6),
        }


def voraz(inst: InstanciaAuditoria, registrar_traza: bool = False) -> ResultadoAuditoria:
    factible, faltan = verificar_factibilidad(inst)
    if not factible:
        raise AuditoriaInfactible(f"ninguna interacción cubre las categorías {faltan}")

    m = _mascaras(inst)
    no_cubiertas = (1 << inst.r) - 1
    elegidas: list[int] = []
    pasos = []
    while no_cubiertas:
        mejor_j, mejor_g = -1, 0
        for j in range(inst.n):
            g = (m[j] & no_cubiertas).bit_count()
            if g > mejor_g:
                mejor_j, mejor_g = j, g
        nuevas = m[mejor_j] & no_cubiertas
        no_cubiertas &= ~m[mejor_j]
        elegidas.append(mejor_j)
        if registrar_traza:
            pasos.append({
                "paso": len(elegidas),
                "interaccion": inst.nombres_interacciones[mejor_j],
                "categorias_nuevas": _nombres_categorias(inst, nuevas),
                "cantidad_nuevas": mejor_g,
                "categorias_restantes": no_cubiertas.bit_count(),
            })

    res = ResultadoAuditoria(
        seleccion=[inst.nombres_interacciones[j] for j in elegidas],
        tamano=len(elegidas), d=inst.d, cota_H_d=armonico(inst.d),
    )
    if registrar_traza:
        res.traza = {
            "factibilidad_verificada": True,
            "elecciones": pasos,
            "verificacion": {"cubre_todas_las_categorias": cubre_todo(inst, elegidas)},
        }
    return res


def exacta(inst: InstanciaAuditoria, max_n: int = MAX_N_EXACTA) -> list[int] | None:
    """Auditoría mínima por fuerza bruta (índices desde 0), o None si n > max_n.

    Recorre los subconjuntos por tamaño creciente y se detiene en el primer
    tamaño que cubre; en el peor caso revisa los 2^n subconjuntos.
    """
    if inst.n > max_n:
        return None
    factible, faltan = verificar_factibilidad(inst)
    if not factible:
        raise AuditoriaInfactible(f"ninguna interacción cubre las categorías {faltan}")
    m = _mascaras(inst)
    universo = (1 << inst.r) - 1
    for k in range(inst.n + 1):
        for combo in combinations(range(inst.n), k):
            union = 0
            for j in combo:
                union |= m[j]
            if union == universo:
                return list(combo)
    return None  # inalcanzable si la instancia es factible
