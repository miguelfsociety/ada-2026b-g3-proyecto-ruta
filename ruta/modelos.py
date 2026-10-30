"""Modelos de datos de las dos partes del problema.

Convenciones (ver la formalización del informe):
- Las etapas y las interacciones se numeran desde 1 en la salida, pero
  internamente se guardan en listas indexadas desde 0.
- Los costos c_i y el presupuesto B son enteros, porque la programación
  dinámica indexa su tabla por presupuesto. Las duraciones t_i y las
  reducciones d_i pueden ser enteras o reales, con 0 <= d_i <= t_i.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Etapa:
    """Una etapa de la cadena: duración normal t, costo de acelerar c y reducción d."""

    t: float
    c: int
    d: float
    nombre: str = ""


@dataclass
class InstanciaAceleracion:
    """Parte 1: cadena de n etapas en serie y presupuesto B."""

    etapas: list[Etapa]
    presupuesto: int

    @property
    def n(self) -> int:
        return len(self.etapas)

    @property
    def duracion_normal(self) -> float:
        return sum(e.t for e in self.etapas)


@dataclass
class InstanciaAuditoria:
    """Parte 2: r categorías de riesgo y n interacciones candidatas.

    `interacciones[j]` es el conjunto de categorías (índices 0..r-1) que cubre
    la interacción j si se audita.
    """

    categorias: list[str]
    interacciones: list[frozenset[int]]
    nombres_interacciones: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.nombres_interacciones:
            self.nombres_interacciones = [str(j + 1) for j in range(len(self.interacciones))]

    @property
    def n(self) -> int:
        return len(self.interacciones)

    @property
    def r(self) -> int:
        return len(self.categorias)

    @property
    def d(self) -> int:
        """Máximo de categorías que cubre una sola interacción."""
        return max((len(s) for s in self.interacciones), default=0)


@dataclass
class Caso:
    """Un caso de prueba: puede traer una o las dos partes."""

    id: str
    aceleracion: InstanciaAceleracion | None
    auditoria: InstanciaAuditoria | None
    origen: str = ""
