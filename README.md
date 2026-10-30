Proyecto Ruta — Solución base (ADA 2026-B, Grupo 3)
Repositorio: https://github.com/miguelfsociety/ada-2026b-g3-proyecto-ruta
Integrantes: Jeison Steven Franco y Miguel Angel Gómez Sánchez.
Solución base del Proyecto Ruta de Análisis y Diseño de Algoritmos:
Parte 1 — Aceleración de la cadena bajo presupuesto. Programación dinámica tipo Mochila 0/1, exacta, en Θ(n·B) tiempo y memoria, con reconstrucción de las etapas aceleradas en Θ(n).
Parte 2 — Cobertura mínima de auditoría. Algoritmo voraz de Cobertura de Conjuntos en O(n·r·min(n, r)), con garantía H(d) ≤ H_r veces el óptimo. Para instancias pequeñas (n ≤ 20) se calcula además el óptimo exacto por fuerza bruta y se verifica la garantía.
Por cada caso se reporta el resultado, el tiempo de ejecución y una traza: estados y decisiones de la programación dinámica, etapas aceleradas, costos y elecciones de la cobertura de auditoría.
Versión del código: 0.1.0 (también en `ruta/__init__.py` y en cada archivo de resultados).
Requisitos
Python 3.10 o superior. La solución base usa solo la biblioteca estándar.
`pytest`, solo para correr las pruebas (`requirements-dev.txt`).
Instalación
```bash
git clone https://github.com/miguelfsociety/ada-2026b-g3-proyecto-ruta.git
cd ada-2026b-g3-proyecto-ruta
python -m venv .venv
source .venv/bin/activate          # En Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt   # opcional, solo para las pruebas
```
Uso rápido
Ejecutar todos los casos de la carpeta `casos/` y guardar las evidencias en `resultados/`:
```bash
python -m ruta.ejecutar casos --salida resultados
```
Ejecutar los casos de la profesora (por ejemplo, copiados en `casos_profesora/`):
```bash
python -m ruta.ejecutar casos_profesora --salida resultados_profesora
```
Opciones:
Opción	Valor por defecto	Descripción
`rutas`	`casos`	Archivos `.json` o carpetas con casos
`--salida`	`resultados`	Carpeta donde se escriben las evidencias
`--repeticiones`	`5`	Repeticiones para medir el tiempo (se reporta mediana y mínimo)
`--max-n-exacta`	`20`	n máximo para calcular el óptimo exacto de auditoría; `-1` lo desactiva
Formato de entrada
Cada caso es un archivo JSON. Puede traer una o las dos partes.
```json
{
  "id": "caso_01",
  "aceleracion": {
    "presupuesto": 6,
    "etapas": [
      {"t": 5, "c": 3, "d": 2},
      [8, 4, 5]
    ]
  },
  "auditoria": {
    "categorias": 5,
    "interacciones": [[1, 2, 3], [3, 4], [4, 5], [1, 5]]
  }
}
```
Etapas: objeto `{"t", "c", "d"}` (con `"nombre"` opcional) o lista `[t, c, d]`. `t` es la duración normal, `c` el costo de acelerar y `d` la reducción.
Condiciones verificadas al leer: `c` y `presupuesto` enteros ≥ 0; `t` y `d` numéricos con 0 ≤ d ≤ t.
Categorías: un entero r (las categorías son 1..r) o una lista de nombres, por ejemplo `["sesgo", "privacidad"]`.
Interacciones: lista de categorías que cubre cada una, o un objeto `{"id": "I1", "cubre": [...]}`.
Antes del voraz se verifica que la unión de todas las interacciones cubra las r categorías.
Un caso con errores se informa en pantalla y en `resumen.csv`, y la ejecución continúa con los demás.
Salida
Por cada caso, en la carpeta de salida:
Archivo	Contenido
`<id>.json`	Resultado, tiempos (todas las mediciones, mediana y mínimo), traza completa y metadatos (versión del código, fecha, versión de Python, plataforma)
`<id>_traza.txt`	La misma información en texto legible: tabla DP y matriz de decisiones (si la tabla tiene ≤ 600 celdas), reconstrucción paso a paso, elecciones del voraz y verificación contra el óptimo
`resumen.csv`	Una fila por caso y parte: tamaño, resultado, tiempo y detalle
Los tiempos se miden con `time.perf_counter`, solo sobre el algoritmo (sin lectura ni escritura de archivos) y sin registrar traza.
Generar casos sintéticos
```bash
python -m ruta.generador --id caso_07 --n 30 --B 100 --interacciones 15 --categorias 25 --semilla 7 --salida casos
```
La misma semilla produce siempre el mismo caso.
Pruebas
```bash
python -m pytest -q
```
Incluyen la comparación de la programación dinámica contra fuerza bruta en 40 instancias aleatorias, la verificación de la cota H(d) del voraz contra el óptimo exacto en otras 40, los ejemplos del informe y los errores de formato.
Estructura del repositorio
```text
ada-2026b-g3-proyecto-ruta/
├── ruta/
│   ├── __init__.py       versión del código
│   ├── modelos.py        estructuras de datos de las instancias
│   ├── io_casos.py       lectura y validación de casos JSON (único módulo que conoce el formato)
│   ├── aceleracion.py    Parte 1: programación dinámica y reconstrucción
│   ├── auditoria.py      Parte 2: factibilidad, voraz y método exacto pequeño
│   ├── ejecutar.py       ejecución por línea de comandos, tiempos y trazas
│   └── generador.py      generador de casos sintéticos con semilla
├── casos/                casos de ejemplo
├── resultados/           evidencias de los casos de ejemplo
├── tests/                pruebas automáticas
├── requirements.txt
└── requirements-dev.txt
```
Casos de ejemplo incluidos
Caso	Propósito
`caso_01_formalizacion`	Ejemplos del informe; óptimos conocidos (D* = 15, auditoría mínima 2)
`caso_02_reducciones`	Instancias que producen las reducciones de NP-dureza del informe
`caso_03_voraz_no_optimo`	El voraz usa 3 auditorías y el óptimo 2; presupuesto que alcanza para todo
`caso_04` a `caso_06`	Sintéticos de tamaño creciente (semillas 1, 2 y 3)
Limitaciones
La programación dinámica es pseudo-polinomial: su tabla tiene (n + 1)(B′ + 1) celdas, con B′ = mín(B, Σcᵢ). Por encima de 50 millones de celdas el programa se detiene con un mensaje en lugar de agotar la memoria.
El voraz de auditoría no garantiza el óptimo, solo un factor H(d). El óptimo exacto solo se calcula para n ≤ 20, porque su costo crece como 2ⁿ.
Los empates del voraz se resuelven a favor de la interacción de menor índice; en la programación dinámica, un empate se resuelve sin acelerar la etapa.
Esta versión no incluye las variantes (cobertura ponderada, presupuesto conjunto, etapas en paralelo).