"""Generador reproducible de casos sintéticos (semilla fija).

Uso:
    python -m ruta.generador --id caso_10 --n 12 --B 40 --interacciones 10 \
        --categorias 15 --semilla 7 --salida casos/

Parte 1: t_i en [1, tmax], d_i en [0, t_i], c_i en [1, cmax].
Parte 2: cada interacción cubre cada categoría con probabilidad p; luego toda
categoría que haya quedado sin cubrir se asigna a una interacción al azar, para
que la instancia sea factible.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path


def generar_caso(caso_id: str, n: int, B: int, n_inter: int, r: int, semilla: int,
                 tmax: int = 20, cmax: int = 10, p: float = 0.25) -> dict:
    rng = random.Random(semilla)
    etapas = []
    for _ in range(n):
        t = rng.randint(1, tmax)
        etapas.append({"t": t, "c": rng.randint(1, cmax), "d": rng.randint(0, t)})

    cubre = [set() for _ in range(n_inter)]
    for j in range(n_inter):
        for k in range(1, r + 1):
            if rng.random() < p:
                cubre[j].add(k)
    if n_inter > 0:
        cubiertas = set().union(*cubre)
        for k in range(1, r + 1):
            if k not in cubiertas:
                cubre[rng.randrange(n_inter)].add(k)

    return {
        "id": caso_id,
        "descripcion": f"sintético: n={n}, B={B}, interacciones={n_inter}, r={r}, semilla={semilla}",
        "aceleracion": {"presupuesto": B, "etapas": etapas},
        "auditoria": {"categorias": r, "interacciones": [sorted(s) for s in cubre]},
    }


def main(argv: list[str] | None = None) -> int:
    a = argparse.ArgumentParser(description="Genera un caso sintético reproducible.")
    a.add_argument("--id", required=True)
    a.add_argument("--n", type=int, required=True, help="número de etapas")
    a.add_argument("--B", type=int, required=True, help="presupuesto")
    a.add_argument("--interacciones", type=int, required=True)
    a.add_argument("--categorias", type=int, required=True)
    a.add_argument("--semilla", type=int, required=True)
    a.add_argument("--p", type=float, default=0.25, help="probabilidad de cobertura")
    a.add_argument("--salida", default="casos")
    args = a.parse_args(argv)
    caso = generar_caso(args.id, args.n, args.B, args.interacciones, args.categorias,
                        args.semilla, p=args.p)
    destino = Path(args.salida)
    destino.mkdir(parents=True, exist_ok=True)
    ruta = destino / f"{args.id}.json"
    ruta.write_text(json.dumps(caso, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Caso escrito en {ruta}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
