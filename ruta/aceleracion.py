"""Parte 1 — Aceleración óptima de la cadena bajo presupuesto.

Programación dinámica tipo Mochila 0/1 (valor d_i, peso c_i, capacidad B):

    DP[0][b] = 0
    DP[i][b] = max(DP[i-1][b], DP[i-1][b - c_i] + d_i)   si c_i <= b
    DP[i][b] = DP[i-1][b]                                 si c_i >  b

DP[i][b] es la mayor reducción de tiempo usando solo las etapas 1..i con
costo a lo sumo b. Tiempo Θ(n·B') y memoria Θ(n·B'), con
B' = min(B, sum c_i) (si el presupuesto alcanza para todo, acelerar todas
las etapas es óptimo porque d_i >= 0). La reconstrucción cuesta Θ(n).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .modelos import InstanciaAceleracion

# Límite de seguridad para la tabla (celdas). Por encima se aborta con un
# mensaje claro en vez de agotar la memoria (el algoritmo es pseudo-polinomial).
LIMITE_CELDAS = 50_000_000
# La tabla completa solo se copia a la traza si es pequeña.
LIMITE_CELDAS_TRAZA = 600


class PresupuestoDemasiadoGrande(MemoryError):
    pass


@dataclass
class ResultadoAceleracion:
    etapas_aceleradas: list[int]          # índices desde 1, en orden creciente
    costo: int
    reduccion: float
    duracion_normal: float
    duracion_minima: float
    presupuesto: int
    presupuesto_efectivo: int
    traza: dict = field(default_factory=dict)

    def como_dict(self) -> dict:
        return {
            "etapas_aceleradas": self.etapas_aceleradas,
            "costo_total": self.costo,
            "presupuesto": self.presupuesto,
            "reduccion_total": self.reduccion,
            "duracion_normal": self.duracion_normal,
            "duracion_minima": self.duracion_minima,
        }


def resolver(inst: InstanciaAceleracion, registrar_traza: bool = False) -> ResultadoAceleracion:
    n = inst.n
    c = [e.c for e in inst.etapas]
    d = [e.d for e in inst.etapas]
    B = inst.presupuesto
    Bef = min(B, sum(c))  # presupuesto efectivo

    if (n + 1) * (Bef + 1) > LIMITE_CELDAS:
        raise PresupuestoDemasiadoGrande(
            f"la tabla tendría {(n + 1) * (Bef + 1):,} celdas (límite {LIMITE_CELDAS:,}); "
            "la programación dinámica es pseudo-polinomial en B")

    # ---- Llenado de la tabla (líneas 1-9 del pseudocódigo) ----
    DP = [[0] * (Bef + 1) for _ in range(n + 1)]
    celdas_donde_cabe = 0
    for i in range(1, n + 1):
        ci, di = c[i - 1], d[i - 1]
        fila_ant, fila = DP[i - 1], DP[i]
        for b in range(Bef + 1):
            if ci <= b:
                celdas_donde_cabe += 1
                no_tomar = fila_ant[b]
                tomar = fila_ant[b - ci] + di
                fila[b] = tomar if tomar > no_tomar else no_tomar
            else:
                fila[b] = fila_ant[b]

    # ---- Reconstrucción (líneas 11-17) ----
    A: list[int] = []
    b = Bef
    pasos = []
    for i in range(n, 0, -1):
        actual, arriba = DP[i][b], DP[i - 1][b]
        acelerar = actual != arriba
        b_sig = b - c[i - 1] if acelerar else b
        if registrar_traza:
            pasos.append({
                "etapa": i, "b": b, "DP[i][b]": actual, "DP[i-1][b]": arriba,
                "decision": "acelerar" if acelerar else "no acelerar",
                "b_siguiente": b_sig,
            })
        if acelerar:
            A.append(i)
        b = b_sig
    A.reverse()

    costo = sum(c[i - 1] for i in A)
    reduccion = DP[n][Bef]
    resultado = ResultadoAceleracion(
        etapas_aceleradas=A, costo=costo, reduccion=reduccion,
        duracion_normal=inst.duracion_normal,
        duracion_minima=inst.duracion_normal - reduccion,
        presupuesto=B, presupuesto_efectivo=Bef,
    )

    if registrar_traza:
        suma_d = sum(d[i - 1] for i in A)
        traza = {
            "presupuesto_efectivo": Bef,
            "dimension_tabla": [n + 1, Bef + 1],
            "celdas_calculadas": n * (Bef + 1),
            "celdas_donde_la_etapa_cabe": celdas_donde_cabe,
            "decisiones_reconstruccion": pasos,
            "verificacion": {
                "costo_dentro_del_presupuesto": costo <= B,
                "reduccion_coincide_con_tabla": abs(suma_d - reduccion) <= 1e-9 * max(1, abs(reduccion)),
                "d_menor_o_igual_t": all(e.d <= e.t for e in inst.etapas),
            },
        }
        if (n + 1) * (Bef + 1) <= LIMITE_CELDAS_TRAZA:
            traza["tabla_DP"] = [list(f) for f in DP]
            # 1 si en esa celda el máximo eligió acelerar la etapa i
            traza["decisiones_tabla"] = [
                [int(c[i - 1] <= bb and DP[i][bb] != DP[i - 1][bb]) for bb in range(Bef + 1)]
                for i in range(1, n + 1)
            ]
        else:
            traza["tabla_DP"] = "omitida por tamaño (ver LIMITE_CELDAS_TRAZA)"
        resultado.traza = traza
    return resultado
