# Food Price 

Dashboard interactivo en **Flask** sobre la evolución de los precios de los alimentos en distintos países (2010–2025).

- **Aplicación en línea:** https://chamsli.pythonanywhere.com
- **Repositorio:** https://github.com/chamsli/food_price_dashboard/

## Qué muestra la aplicación

Los precios de los alimentos se miden con un **índice** (base 2015 = 100): un índice de 120 significa que la comida cuesta un 20 % más que en 2015.
La aplicación no se limita a mostrar los datos en bruto, sino que los interpreta:

- **Inflación anual:** cuánto sube el índice de un año al siguiente.
- **Subida acumulada:** cuánto han subido los precios desde el primer año con datos de cada país.
- **Fiabilidad de los datos:** qué parte de los valores es oficial y cuál es estimada o imputada.
- **Mediana de la inflación mundial:** permite detectar años en los que los precios subieron en casi todos los países a la vez (por ejemplo 2022–2023).

> El índice compara cada país **consigo mismo**; no permite decir que un país tiene la comida más cara que otro, solo que ha subido más o menos.

## Páginas

| Ruta | Contenido |
|---|---|
| `/` | Datos clave, tabla por país y año con filtros (país, rango de años), ordenación por columnas, nivel de detalle básico o completo y paginación. |
| `/graficas` | Tres gráficos con explicación: comparación de países, ranking de inflación de un año y mediana de inflación por año. |
| `/pais/<país>` | Evolución mensual de un país y resumen por año. |
| `/detalle/<año>/<país>` | Detalle mes a mes de un año: índice, variación mensual, mes de mayor subida y fiabilidad de cada dato. |

## Datos

- **Fuente:** FAO, [FAOSTAT – Consumer Price Indices](https://www.fao.org/faostat/en/#data/CP) (portal público de datos abiertos).
- **Serie utilizada:** *Consumer Prices, Food Indices (2015 = 100)*, mensual.
- **Alcance:** 24 países, de 2010 a 2025 (4.608 registros mensuales tras la limpieza).
- **Columnas utilizadas:** `Area` (país), `Year`, `Months Code` (7001 = enero), `Value` (índice) y `Flag` (A = valor oficial, I = valor imputado).
- **Serie descartada:** la serie *Food price inflation* de la propia FAO. La inflación se calcula a partir del índice.

### Limpieza (en `services/data_service.py`)

1. Detección automática de la codificación (UTF-8 o Windows/cp1252) y del separador (coma, punto y coma o tabulador).
2. Conservación de las columnas necesarias y conversión de año, mes y valor a números.
3. Eliminación de filas vacías, inválidas y duplicadas.
4. Conservación de una única serie si el CSV mezcla varias.
5. Marcado de cada valor como oficial o estimado.
6. Cálculo de medias anuales, inflación y subida acumulada.

## Arquitectura

```
food_dashboard/
├── app.py                    # Solo rutas y vistas
├── check_data.py             # Script de comprobación del CSV (no forma parte de la web)
├── requirements.txt
├── data/
│   └── food_prices.csv      # Conjunto de datos
├── services/
│   ├── data_service.py       # Lectura, limpieza y consultas del CSV 
│   └── graph_service.py      # Gráficas con matplotlib
├── templates/                # Plantillas Jinja: base, dashboard, graficas, pais, detalle, 404
└── static/
    └── styles.css            # Estilos
```

Toda la lógica de negocio (consultas, operaciones sobre los datos y creación de gráficas) está en módulos independientes dentro de `services/`.Y `app.py` contiene únicamente las rutas.
Las gráficas se generan con matplotlib en el servidor y se incrustan en la página como imágenes PNG codificadas en base64, por lo que no se escriben archivos en disco.


## Despliegue en PythonAnywhere

1. Sube la carpeta del proyecto (incluido `data/food_prices.csv`) a `/home/TU_USUARIO/flask_dashboard`.
2. En una consola Bash: `mkvirtualenv --python=/usr/bin/python3.10 meuentorn` y `pip install flask matplotlib`.
3. En la pestaña *Web*, crea una aplicación con *Manual configuration* (Python 3.10) e indica la ruta del entorno virtual.
4. En el archivo WSGI usa:
   ```python
   import sys
   project_home = '/home/TU_USUARIO/flask_dashboard'
   if project_home not in sys.path:
       sys.path.insert(0, project_home)
   from app import app as application
   ```
5. Pulsa **Reload** y abre `https://TU_USUARIO.pythonanywhere.com`.

## Limitaciones

- El primer año del conjunto (2010) no tiene inflación anual porque no hay un año anterior con el que compararlo.
- Muchos países publican pocos valores oficiales mensuales; el resto son estimaciones de la FAO o de los institutos nacionales.
