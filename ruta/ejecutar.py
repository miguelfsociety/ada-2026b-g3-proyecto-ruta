"""Ejecuta la solución base sobre uno o varios casos y guarda las evidencias.

Uso:
    python -m ruta.ejecutar casos/ --salida resultados/
    python -m ruta.ejecutar casos/caso_01.json --repeticiones 10

Por cada caso escribe en la carpeta de salida:
    <id>.json        resultado, tiempos y traza completa (formato máquina)
    <id>_traza.txt   la misma información en texto legible
y además un resumen.csv con una fila por caso y parte.

Los tiempos se miden con time.perf_counter, solo sobre el algoritmo (sin
lectura de archivos ni escritura de resultados) y sin registrar traza; se
reporta la mediana y el mínimo de varias repeticiones. La traza se obtiene en
una ejecución adicional.
"""

from __future__ import annotations

import argparse
import csv
import json
import platform
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

from . import __version__
from . import aceleracion, auditoria
from .io_casos import ErrorDeFormato, cargar_caso, listar_casos
from .modelos import Caso


def _medir(funcion, repeticiones: int) -> dict:
    tiempos = []
    for _ in range(repeticiones):
        inicio = time.perf_counter()
        funcion()
        tiempos.append((time.perf_counter() - inicio) * 1000.0)
    return {
        "mediana": round(statistics.median(tiempos), 6),
        "minimo": round(min(tiempos), 6),
        "mediciones": [round(t, 6) for t in tiempos],
    }


def _parte_aceleracion(caso: Caso, repeticiones: int) -> dict:
    inst = caso.aceleracion
    salida = {"instancia": {"n": inst.n, "presupuesto": inst.presupuesto,
                            "duracion_normal": inst.duracion_normal}}
    try:
        salida["tiempo_ms"] = _medir(lambda: aceleracion.resolver(inst), repeticiones)
        res = aceleracion.resolver(inst, registrar_traza=True)
    except aceleracion.PresupuestoDemasiadoGrande as e:
        salida["error"] = str(e)
        return salida
    salida["resultado"] = res.como_dict()
    salida["traza"] = res.traza
    return salida


def _parte_auditoria(caso: Caso, repeticiones: int, max_n_exacta: int) -> dict:
    inst = caso.auditoria
    salida = {"instancia": {"n": inst.n, "r": inst.r, "d": inst.d}}
    factible, faltan = auditoria.verificar_factibilidad(inst)
    salida["factible"] = factible
    if not factible:
        salida["error"] = f"instancia infactible: ninguna interacción cubre {faltan}"
        return salida
    salida["tiempo_ms"] = _medir(lambda: auditoria.voraz(inst), repeticiones)
    res = auditoria.voraz(inst, registrar_traza=True)
    salida["resultado"] = res.como_dict()
    salida["traza"] = res.traza

    if max_n_exacta >= 0 and inst.n <= max_n_exacta:
        inicio = time.perf_counter()
        opt = auditoria.exacta(inst, max_n=max_n_exacta)
        t_exacta = (time.perf_counter() - inicio) * 1000.0
        k_opt = len(opt)
        salida["verificacion_exacta"] = {
            "optimo": k_opt,
            "seleccion_optima": [inst.nombres_interacciones[j] for j in opt],
            "razon_voraz_sobre_optimo": round(res.tamano / k_opt, 6) if k_opt else 1.0,
            "cumple_cota_H_d": res.tamano <= res.cota_H_d * k_opt + 1e-9,
            "tiempo_ms": round(t_exacta, 6),
        }
    else:
        salida["verificacion_exacta"] = f"omitida (n = {inst.n} > {max_n_exacta})"
    return salida


def ejecutar_caso(caso: Caso, repeticiones: int, max_n_exacta: int) -> dict:
    salida: dict = {
        "caso": caso.id,
        "archivo": caso.origen,
        "version_codigo": __version__,
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "python": platform.python_version(),
        "plataforma": platform.platform(),
        "repeticiones": repeticiones,
    }
    if caso.aceleracion is not None:
        salida["aceleracion"] = _parte_aceleracion(caso, repeticiones)
    if caso.auditoria is not None:
        salida["auditoria"] = _parte_auditoria(caso, repeticiones, max_n_exacta)
    return salida


# ---------------------------------------------------------------- texto legible

def _tabla_texto(tabla: list[list], encabezado: str) -> list[str]:
    ancho = max(len(str(x)) for fila in tabla for x in fila)
    ancho = max(ancho, len(str(len(tabla[0]) - 1)))
    lineas = [encabezado,
              "      b = " + " ".join(str(b).rjust(ancho) for b in range(len(tabla[0])))]
    for i, fila in enumerate(tabla):
        lineas.append(f"  i = {i:<3} " + " ".join(str(x).rjust(ancho) for x in fila))
    return lineas


def traza_legible(r: dict) -> str:
    L = [f"Caso: {r['caso']}   (código v{r['version_codigo']}, {r['fecha']}, Python {r['python']})",
         f"Archivo: {r['archivo']}", ""]

    if "aceleracion" in r:
        a = r["aceleracion"]
        L.append("=== Parte 1: aceleración de la cadena (programación dinámica) ===")
        L.append(f"n = {a['instancia']['n']} etapas, presupuesto B = {a['instancia']['presupuesto']}, "
                 f"duración normal = {a['instancia']['duracion_normal']}")
        if "error" in a:
            L += [f"ERROR: {a['error']}", ""]
        else:
            res, tr = a["resultado"], a["traza"]
            L.append(f"Presupuesto efectivo B' = {tr['presupuesto_efectivo']}; tabla "
                     f"{tr['dimension_tabla'][0]} x {tr['dimension_tabla'][1]}; "
                     f"celdas calculadas = {tr['celdas_calculadas']}; "
                     f"celdas donde la etapa cabe = {tr['celdas_donde_la_etapa_cabe']}")
            if isinstance(tr.get("tabla_DP"), list):
                L += _tabla_texto(tr["tabla_DP"], "Tabla DP[i][b] (mayor reducción con etapas 1..i y presupuesto b):")
                L += _tabla_texto([[0] * len(tr["decisiones_tabla"][0])] + tr["decisiones_tabla"],
                                  "Decisiones (1 = el máximo eligió acelerar la etapa i; fila 0 sin decisión):")
            else:
                L.append(f"Tabla DP: {tr['tabla_DP']}")
            L.append("Reconstrucción (de la última etapa a la primera):")
            for p in tr["decisiones_reconstruccion"]:
                L.append(f"  etapa {p['etapa']:>3}: b = {p['b']}, DP[i][b] = {p['DP[i][b]']}, "
                         f"DP[i-1][b] = {p['DP[i-1][b]']} -> {p['decision']} (b siguiente = {p['b_siguiente']})")
            L.append(f"Etapas aceleradas: {res['etapas_aceleradas']}")
            L.append(f"Costo total = {res['costo_total']} <= B = {res['presupuesto']}; "
                     f"reducción = {res['reduccion_total']}; duración mínima = {res['duracion_minima']}")
            L.append(f"Verificación: {tr['verificacion']}")
            L.append(f"Tiempo (ms): mediana = {a['tiempo_ms']['mediana']}, mínimo = {a['tiempo_ms']['minimo']}")
            L.append("")

    if "auditoria" in r:
        a = r["auditoria"]
        L.append("=== Parte 2: cobertura de auditoría (voraz) ===")
        L.append(f"n = {a['instancia']['n']} interacciones, r = {a['instancia']['r']} categorías, "
                 f"d = {a['instancia']['d']}")
        if "error" in a:
            L += [f"ERROR: {a['error']}", ""]
        else:
            res, tr = a["resultado"], a["traza"]
            L.append("Factibilidad verificada: la unión de todas las interacciones cubre las r categorías.")
            L.append("Elecciones del voraz:")
            for p in tr["elecciones"]:
                L.append(f"  paso {p['paso']}: interacción {p['interaccion']} cubre {p['cantidad_nuevas']} "
                         f"nuevas {p['categorias_nuevas']}; quedan {p['categorias_restantes']}")
            L.append(f"Interacciones auditadas: {res['interacciones_auditadas']} "
                     f"({res['numero_de_auditorias']} auditorías)")
            L.append(f"Verificación: {tr['verificacion']}")
            ve = a["verificacion_exacta"]
            if isinstance(ve, dict):
                L.append(f"Óptimo exacto (fuerza bruta): {ve['optimo']} -> {ve['seleccion_optima']}; "
                         f"razón voraz/óptimo = {ve['razon_voraz_sobre_optimo']}; "
                         f"cota H(d) = {res['cota_H_d']}; cumple la cota: {ve['cumple_cota_H_d']}")
            else:
                L.append(f"Verificación exacta: {ve}")
            L.append(f"Tiempo voraz (ms): mediana = {a['tiempo_ms']['mediana']}, mínimo = {a['tiempo_ms']['minimo']}")
            L.append("")
    return "\n".join(L)


# ---------------------------------------------------------------- programa

def _fila_resumen(r: dict, parte: str) -> dict:
    a = r[parte]
    fila = {"caso": r["caso"], "parte": parte, "version_codigo": r["version_codigo"]}
    if parte == "aceleracion":
        fila.update(n=a["instancia"]["n"], B_o_r=a["instancia"]["presupuesto"])
        if "error" in a:
            fila.update(resultado="ERROR", detalle=a["error"])
        else:
            res = a["resultado"]
            fila.update(resultado=res["duracion_minima"],
                        detalle=f"acelerar {res['etapas_aceleradas']}; costo {res['costo_total']}; "
                                f"reducción {res['reduccion_total']}")
    else:
        fila.update(n=a["instancia"]["n"], B_o_r=a["instancia"]["r"])
        if "error" in a:
            fila.update(resultado="ERROR", detalle=a["error"])
        else:
            res = a["resultado"]
            ve = a["verificacion_exacta"]
            extra = f"; óptimo {ve['optimo']}" if isinstance(ve, dict) else ""
            fila.update(resultado=res["numero_de_auditorias"],
                        detalle=f"auditar {res['interacciones_auditadas']}{extra}")
    t = a.get("tiempo_ms")
    fila.update(tiempo_mediana_ms=t["mediana"] if t else "", tiempo_min_ms=t["minimo"] if t else "")
    return fila


_RESERVADOS_WINDOWS = {"CON", "PRN", "AUX", "NUL", *(f"COM{k}" for k in range(1, 10)),
                       *(f"LPT{k}" for k in range(1, 10))}


def nombre_archivo(caso_id: str) -> str:
    """Convierte el id de un caso en un nombre de archivo válido en Windows, Linux y macOS."""
    nombre = "".join("_" if ch in '<>:"/\\|?*' or ord(ch) < 32 else ch for ch in caso_id)
    nombre = nombre.strip(" .") or "caso"
    if nombre.split(".")[0].upper() in _RESERVADOS_WINDOWS:
        nombre = "_" + nombre
    return nombre


def _entero_positivo(texto: str) -> int:
    valor = int(texto)
    if valor < 1:
        raise argparse.ArgumentTypeError(f"debe ser un entero >= 1, se recibió {valor}")
    return valor


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Solución base del Proyecto Ruta (Grupo 3).")
    p.add_argument("rutas", nargs="*", default=["casos"], help="archivos .json o carpetas de casos")
    p.add_argument("--salida", default="resultados", help="carpeta para las evidencias")
    p.add_argument("--repeticiones", type=_entero_positivo, default=5,
                   help="repeticiones para medir el tiempo (>= 1)")
    p.add_argument("--max-n-exacta", type=int, default=auditoria.MAX_N_EXACTA,
                   help="n máximo para calcular el óptimo exacto de auditoría (-1 para desactivar)")
    args = p.parse_args(argv)

    archivos = listar_casos(args.rutas)
    if not archivos:
        print("No se encontraron casos .json", file=sys.stderr)
        return 1
    salida = Path(args.salida)
    salida.mkdir(parents=True, exist_ok=True)

    filas, errores = [], 0
    usados: set[str] = set()  # en minúsculas: Windows no distingue mayúsculas en nombres de archivo
    for archivo in archivos:
        try:
            caso = cargar_caso(archivo)
        except (ErrorDeFormato, OSError) as e:
            errores += 1
            print(f"[ERROR] {archivo}: {e}", file=sys.stderr)
            filas.append({"caso": archivo.stem, "parte": "lectura", "resultado": "ERROR", "detalle": str(e)})
            continue
        base = nombre = nombre_archivo(caso.id)
        k = 2
        while nombre.lower() in usados:
            nombre, k = f"{base}_{k}", k + 1
        usados.add(nombre.lower())
        if nombre != caso.id:
            print(f"[AVISO] {archivo}: el caso '{caso.id}' se guarda como '{nombre}' "
                  "(id repetido o con caracteres no válidos en un nombre de archivo)", file=sys.stderr)
        r = ejecutar_caso(caso, args.repeticiones, args.max_n_exacta)
        (salida / f"{nombre}.json").write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
        (salida / f"{nombre}_traza.txt").write_text(traza_legible(r), encoding="utf-8")
        for parte in ("aceleracion", "auditoria"):
            if parte in r:
                filas.append(_fila_resumen(r, parte))
        print(f"[OK] {caso.id}")

    campos = ["caso", "parte", "version_codigo", "n", "B_o_r", "resultado",
              "tiempo_mediana_ms", "tiempo_min_ms", "detalle"]
    with open(salida / "resumen.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore")
        w.writeheader()
        w.writerows(filas)
    print(f"Evidencias en {salida}/ ({len(archivos) - errores} casos procesados, {errores} con error)")
    return 0 if errores == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
