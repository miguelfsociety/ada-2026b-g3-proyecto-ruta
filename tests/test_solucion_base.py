"""Pruebas de la solución base. Ejecutar con:  python -m pytest -q"""

import json
import random
from itertools import combinations

import pytest

from ruta import aceleracion, auditoria, ejecutar
from ruta.generador import generar_caso
from ruta.io_casos import ErrorDeFormato, cargar_caso, caso_desde_dict
from ruta.modelos import Etapa, InstanciaAceleracion, InstanciaAuditoria


# ------------------------------------------------------------ Parte 1

def _fuerza_bruta_aceleracion(inst):
    mejor = 0
    for k in range(inst.n + 1):
        for A in combinations(range(inst.n), k):
            if sum(inst.etapas[i].c for i in A) <= inst.presupuesto:
                mejor = max(mejor, sum(inst.etapas[i].d for i in A))
    return mejor


def test_ejemplo_formalizacion():
    inst = InstanciaAceleracion(
        etapas=[Etapa(5, 3, 2), Etapa(8, 4, 5), Etapa(6, 2, 3), Etapa(4, 3, 1)], presupuesto=6)
    res = aceleracion.resolver(inst, registrar_traza=True)
    assert res.etapas_aceleradas == [2, 3]
    assert res.reduccion == 8 and res.duracion_minima == 15 and res.costo == 6
    assert res.traza["tabla_DP"][4] == [0, 0, 3, 3, 5, 5, 8]


def test_ejemplo_reduccion_mochila():
    # mochila w=(3,4,2), v=(4,5,3), W=5, V=7 -> L = 12 - 7 = 5 (respuesta SÍ)
    inst = InstanciaAceleracion(etapas=[Etapa(4, 3, 4), Etapa(5, 4, 5), Etapa(3, 2, 3)], presupuesto=5)
    res = aceleracion.resolver(inst)
    assert res.duracion_minima == 5 and res.etapas_aceleradas == [1, 3]


@pytest.mark.parametrize("semilla", range(40))
def test_dp_igual_a_fuerza_bruta(semilla):
    rng = random.Random(semilla)
    n = rng.randint(0, 9)
    etapas = []
    for _ in range(n):
        t = rng.randint(0, 15)
        etapas.append(Etapa(t, rng.randint(1, 8), rng.randint(0, t)))
    inst = InstanciaAceleracion(etapas=etapas, presupuesto=rng.randint(0, 25))
    res = aceleracion.resolver(inst, registrar_traza=True)
    assert res.reduccion == _fuerza_bruta_aceleracion(inst)
    assert res.costo <= inst.presupuesto
    assert sum(inst.etapas[i - 1].d for i in res.etapas_aceleradas) == res.reduccion
    assert all(res.traza["verificacion"].values())


def test_presupuesto_efectivo_y_limite():
    inst = InstanciaAceleracion(etapas=[Etapa(5, 2, 1), Etapa(5, 3, 2)], presupuesto=10**12)
    res = aceleracion.resolver(inst)
    assert res.presupuesto_efectivo == 5 and res.etapas_aceleradas == [1, 2]
    grande = InstanciaAceleracion(etapas=[Etapa(1, 10**9, 1), Etapa(1, 10**9, 1)], presupuesto=10**9)
    with pytest.raises(aceleracion.PresupuestoDemasiadoGrande):
        aceleracion.resolver(grande)


# ------------------------------------------------------------ Parte 2

def _inst_aud(r, conjuntos):
    return InstanciaAuditoria(categorias=[str(k + 1) for k in range(r)],
                              interacciones=[frozenset(s) for s in conjuntos])


def test_voraz_no_optimo():
    inst = _inst_aud(6, [{0, 1, 2}, {3, 4, 5}, {0, 1, 3, 4}])
    assert auditoria.voraz(inst).tamano == 3
    assert len(auditoria.exacta(inst)) == 2


def test_infactible():
    inst = _inst_aud(3, [{0}, {1}])
    assert auditoria.verificar_factibilidad(inst) == (False, ["3"])
    with pytest.raises(auditoria.AuditoriaInfactible):
        auditoria.voraz(inst)


@pytest.mark.parametrize("semilla", range(40))
def test_voraz_cubre_y_respeta_cota(semilla):
    caso = caso_desde_dict(generar_caso("t", 1, 1, n_inter=random.Random(semilla).randint(1, 10),
                                        r=random.Random(semilla + 99).randint(0, 14), semilla=semilla))
    inst = caso.auditoria
    res = auditoria.voraz(inst, registrar_traza=True)
    assert res.traza["verificacion"]["cubre_todas_las_categorias"]
    opt = auditoria.exacta(inst)
    assert auditoria.cubre_todo(inst, opt)
    assert len(opt) <= res.tamano <= auditoria.armonico(inst.d) * len(opt) + 1e-9


# ------------------------------------------------------------ Lectura de casos

def test_formatos_equivalentes():
    a = caso_desde_dict({"aceleracion": {"presupuesto": 3, "etapas": [[4, 1, 2]]},
                         "auditoria": {"categorias": 2, "interacciones": [[1, 2]]}})
    b = caso_desde_dict({"aceleracion": {"presupuesto": 3, "etapas": [{"t": 4, "c": 1, "d": 2}]},
                         "auditoria": {"categorias": ["x", "y"],
                                       "interacciones": [{"id": "1", "cubre": ["x", "y"]}]}})
    ea, eb = a.aceleracion.etapas[0], b.aceleracion.etapas[0]
    assert (ea.t, ea.c, ea.d) == (eb.t, eb.c, eb.d)
    assert a.auditoria.interacciones == b.auditoria.interacciones


@pytest.mark.parametrize("datos", [
    {"aceleracion": {"presupuesto": 3, "etapas": [[4, 1, 5]]}},           # d > t
    {"aceleracion": {"presupuesto": 2.5, "etapas": [[4, 1, 2]]}},         # B no entero
    {"aceleracion": {"presupuesto": 3, "etapas": [[4, 1.5, 2]]}},         # c no entero
    {"auditoria": {"categorias": 2, "interacciones": [[1, 3]]}},          # categoría fuera de rango
    {"auditoria": {"categorias": ["a"], "interacciones": [["b"]]}},       # categoría desconocida
    {"id": "vacio"},                                                     # sin partes
    {"aceleracion": [1, 2]},                                             # parte que no es objeto
    {"aceleracion": {"presupuesto": 3, "etapas": 5}},                    # etapas no es lista
    {"auditoria": "x"},                                                  # parte que no es objeto
    {"auditoria": {"categorias": 2, "interacciones": 7}},                # interacciones no es lista
])
def test_errores_de_formato(datos):
    with pytest.raises(ErrorDeFormato):
        caso_desde_dict(datos)


def test_generador_reproducible():
    assert json.dumps(generar_caso("x", 8, 20, 6, 9, semilla=5)) == \
        json.dumps(generar_caso("x", 8, 20, 6, 9, semilla=5))


def test_archivo_con_bom_y_no_utf8(tmp_path):
    con_bom = tmp_path / "bom.json"
    con_bom.write_bytes(b"\xef\xbb\xbf" + json.dumps({"auditoria": {"categorias": 1, "interacciones": [[1]]}}).encode())
    assert cargar_caso(con_bom).auditoria.r == 1
    latin1 = tmp_path / "latin1.json"
    latin1.write_bytes('{"id": "año", "auditoria": {"categorias": 1, "interacciones": [[1]]}}'.encode("latin-1"))
    with pytest.raises(ErrorDeFormato):
        cargar_caso(latin1)


# ------------------------------------------------------------ Ejecución por línea de comandos

def test_nombre_archivo():
    assert ejecutar.nombre_archivo("caso_01") == "caso_01"
    assert ejecutar.nombre_archivo("a/b:c*") == "a_b_c_"
    assert ejecutar.nombre_archivo(" . ") == "caso"
    assert ejecutar.nombre_archivo("con") == "_con"


def test_ejecucion_continua_con_casos_malos(tmp_path):
    casos = tmp_path / "casos"
    casos.mkdir()
    bueno = {"auditoria": {"categorias": 1, "interacciones": [[1]]}}
    (casos / "a_etapas_num.json").write_text('{"aceleracion": {"presupuesto": 3, "etapas": 5}}')
    (casos / "b_latin1.json").write_bytes('{"id": "ñ"}'.encode("latin-1"))
    (casos / "c_id_barra.json").write_text(json.dumps({"id": "x/y", **bueno}))
    (casos / "d_dup.json").write_text(json.dumps({"id": "rep", **bueno}))
    (casos / "e_dup.json").write_text(json.dumps({"id": "rep", **bueno}))
    salida = tmp_path / "res"
    assert ejecutar.main([str(casos), "--salida", str(salida), "--repeticiones", "1"]) == 2
    escritos = {p.name for p in salida.glob("*.json")}
    assert escritos == {"x_y.json", "rep.json", "rep_2.json"}
    filas = (salida / "resumen.csv").read_text(encoding="utf-8").splitlines()
    assert len(filas) == 1 + 5  # encabezado + 2 errores de lectura + 3 casos


def test_repeticiones_debe_ser_positivo(tmp_path):
    with pytest.raises(SystemExit):
        ejecutar.main(["casos", "--salida", str(tmp_path), "--repeticiones", "0"])
