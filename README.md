# PROYECTO: Data Warehouse de Comercio Exterior (Aduana)

## 📋 Descripción General

Este proyecto implementa un **Data Warehouse (DW)** completo para análisis de datos aduanales de importaciones y exportaciones. Utiliza arquitectura de **capas de datos (Data Lake)** y modelo **estrella (Star Schema)** para BI analítica.

**Objetivo:** Transformar datos crudos aduanales en información estructurada para análisis, reportes y visualización.

---

## 🏗️ Arquitectura del Proyecto

```
PARQUET CRUDO (Bronze)
         ↓
    ETL (Normalización)
         ↓
STAGING (Temporales)
         ↓
    ETL (Dimensiones)
         ↓
DIMENSIONES (Silver) ──┐
                       ├─→ TABLA DE HECHOS (Gold)
DATA MARTS (OLAP)      │
                       ↓
   REPORTES GRÁFICOS ← ANÁLISIS
```

### Capas del Data Lake

| Capa       | Ubicación           | Contenido                       | Propósito            |
| ---------- | ------------------- | ------------------------------- | -------------------- |
| **Bronze** | `data_lake/bronze/` | Datos crudos (parquet original) | Ingesta sin procesar |
| **Silver** | `data_lake/silver/` | Dimensiones limpias             | Datos reutilizables  |
| **Gold**   | `data_lake/gold/`   | Tabla de hechos                 | Modelo para BI       |

---

## 🚀 Instalación y Configuración

### Requisitos Previos

- **Python 3.8+**
- **pip** (gestor de paquetes Python)
- **DuckDB** (base de datos embebida)

### Paso 1: Clonar o descargar el proyecto

```bash
cd C:\curso-bi
```

### Paso 2: Crear entorno virtual

```bash
python -m venv venv
```

### Paso 3: Activar entorno virtual

**Windows:**

```bash
venv\Scripts\activate
```

**Linux/Mac:**

```bash
source venv/bin/activate
```

### Paso 4: Instalar dependencias

```bash
pip install -r requirements.txt
```

**Contenido de requirements.txt:**

```
duckdb==1.0.0
pandas==2.2.0
matplotlib==3.8.0
seaborn==0.13.0
numpy==1.24.0
```

O instalar manualmente:

```bash
pip install duckdb pandas matplotlib seaborn
```

### Paso 5: Preparar datos

1. Colocar archivo `aduana_item_raw.parquet` en:

   ```
   C:\curso-bi\data_lake\bronze\aduana_item_raw.parquet
   ```

2. Crear carpeta de base de datos:
   ```bash
   mkdir db
   ```

---

## 📁 Estructura del Proyecto

```
curso-bi/
│
├── sql/                      # Creación de esquema DW
│   ├── crear-tablas.py      # Crea estructura (staging + dims + hechos)
│   └── verificar-creacion-tablas.py  # Valida tablas creadas
│
├── etl/                      # Procesos de extracción-transformación-carga
│   ├── etl-cargar-staging.py        # Lee parquet, normaliza, carga staging
│   ├── etl-dimensiones.py           # Construye dimensiones (Dim_*)
│   └── etl-fact.py                  # Construye tabla de hechos
│
├── olap/                     # Tablas agregadas y vistas analíticas
│   ├── analitica-vistas.py          # Crea vistas SQL para reportes
│   ├── analitica-tablas-agregadas.py # Tablas precalculadas (agg_*)
│   └── analitica-consultas.py       # Consultas analíticas de ejemplo
│
├── helpers/                  # Utilitarios
│   ├── export-parquet-bronze.py     # Importa datos a Bronze
│   └── exportar-parquet.py          # Exporta DW a parquet (Silver/Gold)
│
├── graficos/                 # Generación de reportes visuales
│   └── graficos.py           # Crea 6 gráficos PNG para BI
│
├── data_lake/                # Almacenamiento de datos
│   ├── bronze/               # Datos crudos (parquet original)
│   ├── silver/               # Dimensiones procesadas
│   ├── gold/                 # Tabla de hechos
│   └── reportes_graficos/    # Gráficos generados
│
├── db/                       # Base de datos
│   └── aduana.duckdb         # DuckDB (se crea al ejecutar)
│
├── venv/                     # Entorno virtual Python
│
├── .gitignore                # Configuración de Git
└── README.md                 # Este archivo
```

---

## ⚙️ Flujo de Ejecución

### 1. Inicializar Base de Datos

```bash
cd C:\curso-bi
python sql/crear-tablas.py
```

**Qué hace:**

- Crea schema `dw`
- Crea tabla de staging `dw.stg_aduana`
- Crea 7 dimensiones (Fecha, Producto, Aduana, Países, Operación, Régimen)
- Crea tabla de hechos `dw.Fact_Aduana_Item`

**Resultado:** Archivo `db/aduana.duckdb` creado

---

### 2. Cargar Datos de Staging

```bash
python etl/etl-cargar-staging.py
```

**Qué hace:**

- Lee archivo `aduana_item_raw.parquet` (datos crudos)
- Normaliza datos:
  - Conversión de tipos (strings → números, fechas)
  - Normalización de separadores decimales (coma → punto)
  - Limpieza de países (prefijos, caracteres corruptos)
  - Conversión a mayúsculas
- Carga en `dw.stg_aduana` con validaciones

**Filtros:**

- Solo datos de 2025 en adelante
- Excluye registros con FOB = 0

**Resultado:** ✓ STAGING OK: X,XXX,XXX filas | batch: BATCH_20250604_153022

---

### 3. Construir Dimensiones

```bash
python etl/etl-dimensiones.py
```

**Qué hace:**

- Lee datos de staging
- Crea dimensiones deduplicadas con claves numéricas:
  - `dw.Dim_Fecha`: Calendario 2025
  - `dw.Dim_Producto`: Catálogo de posiciones NCM
  - `dw.Dim_Aduana`: Puntos aduaneros
  - `dw.Dim_Pais_Origen`: Países de origen
  - `dw.Dim_Pais_Destino`: Países destino
  - `dw.Dim_Operacion`: Importación/Exportación
  - `dw.Dim_Regimen`: Regímenes aduanales

**Resultado:** 7 dimensiones pobladas con datos únicos

---

### 4. Construir Tabla de Hechos

```bash
python etl/etl-fact.py
```

**Qué hace:**

- Lee datos de staging
- Busca claves en dimensiones (surrogate keys)
- Construye tabla `dw.Fact_Aduana_Item`:
  - 1 fila = 1 ítem de 1 despacho
  - Contiene todas las métricas (FOB, fletes, gravámenes, pesos)
  - Conecta a 8 dimensiones mediante claves foráneas

**Modelo:** Star Schema (estrella)

**Resultado:** Millones de filas en Fact_Aduana_Item

---

### 5. Crear Tablas Agregadas OLAP

```bash
python olap/analitica-tablas-agregadas.py
```

**Qué hace:**

- Precomputa agregaciones para análisis rápidos
- Crea 5 tablas en schema `analytic`:
  - `agg_fob_mensual_operacion`: FOB por mes × tipo operación
  - `agg_fob_pais_anual`: FOB por país × año
  - `agg_fob_aduana_mensual`: FOB por aduana × mes
  - `agg_fob_ncm_anual`: FOB por posición NCM × año
  - `agg_canal_mensual`: Canales de control VERDE/ROJO/NARANJA

**Beneficio:** Queries de reportes mucho más rápidas

---

### 6. Crear Vistas Analíticas

```bash
python olap/analitica-vistas.py
```

**Qué hace:**

- Crea 6 vistas SQL reutilizables:
  - `v_fob_por_operacion`: Comparación IMP vs EXP
  - `v_top_paises`: Ranking de países
  - `v_tendencia_mensual`: Evolución mes a mes
  - `v_ranking_aduana`: Ranking de aduanas
  - `v_top_ncm`: Productos más movidos
  - `v_canal_control`: Distribución de canales

**Beneficio:** Abstraer lógica SQL, reutilizar en reportes

---

### 7. Ejecutar Consultas Analíticas

```bash
python olap/analitica-consultas.py
```

**Qué hace:**

- Ejecuta 7 consultas analíticas de ejemplo
- Muestra resultados en terminal
- Valida integridad de datos

**Ejemplos:**

- R1: FOB por operación con variación anual (YoY)
- R2: Top 10 países origen (año reciente)
- R3: Tendencia mensual FOB
- R4: Ranking aduanas por FOB
- R5: Top 10 NCM por valor
- R6: Canal de control (VERDE/ROJO/NARANJA)
- BONUS: Países con mayor proporción ROJO

---

### 8. Generar Reportes Gráficos

```bash
python graficos/graficos.py
```

**Qué hace:**

- Genera 6 reportes en PNG (300 DPI):
  1. `1_fob_por_operacion.png` - Línea: tendencia anual
  2. `2_top_10_paises.png` - Barras: socios comerciales
  3. `3_tendencia_mensual.png` - Línea: evolución YTD
  4. `4_ranking_aduanas.png` - Barras: por operación
  5. `5_top_10_ncm.png` - Barras: productos top
  6. `6_canal_control.png` - Barras apiladas: canales

**Ubicación:** `data_lake/reportes_graficos/`

---

### 9. Exportar a Parquet (Silver/Gold)

```bash
python helpers/exportar-parquet.py
```

**Qué hace:**

- Exporta dimensiones a `data_lake/silver/`
- Exporta tabla de hechos a `data_lake/gold/`
- Formato: Parquet con compresión ZSTD

**Beneficio:** Integración con Power BI, Python, Tableau

---

## 📊 Esquema de Base de Datos

### Dimensiones (Silver)

```
DIM_FECHA                    DIM_PRODUCTO
├─ fecha_key (PK)           ├─ producto_key (PK)
├─ fecha_oficializacion      ├─ rubro
├─ anio                      ├─ capitulo
├─ mes_nombre                ├─ partida
├─ mes_numero                ├─ posicion
├─ trimestre                 └─ descripcion_arancelaria
└─ semestre
                             DIM_ADUANA
DIM_PAIS_ORIGEN              ├─ aduana_key (PK)
├─ pais_origen_key (PK)      ├─ nombre_aduana
└─ pais_origen_desc          └─ ubicacion_dependencia

DIM_PAIS_DESTINO             DIM_OPERACION
├─ pais_destino_key (PK)     ├─ operacion_key (PK)
└─ pais_desc_desc            └─ tipo_operacion

DIM_REGIMEN
├─ regimen_key (PK)
├─ codigo_regimen
└─ descripcion_regimen
```

### Tabla de Hechos (Gold)

```
FACT_ADUANA_ITEM (estrella)
├─ id_fact_key (PK)
├─ fecha_key (FK → Dim_Fecha)
├─ aduana_key (FK → Dim_Aduana)
├─ producto_key (FK → Dim_Producto)
├─ pais_origen_key (FK → Dim_Pais_Origen)
├─ pais_destino_key (FK → Dim_Pais_Destino)
├─ operacion_key (FK → Dim_Operacion)
├─ regimen_key (FK → Dim_Regimen)
│
├─ MÉTRICAS:
├─ kilo_neto / kilo_bruto    (pesos en kg)
├─ fob_dolar (FOB en USD)
├─ flete_dolar / seguro_dolar (gastos)
├─ derecho / isc / iva (gravámenes)
├─ total_gravamen (suma gravámenes)
│
├─ AUDITORÍA:
├─ canal (V/R/N - control)
├─ batch_id (lote ETL)
└─ fecha_carga (timestamp)
```

---

## 📈 Métricas Disponibles

### FOB (Free On Board)

- Base de cálculo del arancel
- Valor de mercancía sin incluir flete/seguro

### Gravámenes Aduanales

- **Derecho:** Arancel específico por posición
- **ISC:** Impuesto Selectivo al Consumo
- **IVA:** Impuesto al Valor Agregado (típicamente 10%)
- **Servicio:** Tasa de servicios aduanales

### Pesos

- **Kilo Neto:** Peso sin envase
- **Kilo Bruto:** Peso total con envase

### Canal de Control

- **VERDE (V):** Riesgo bajo - Despacho automático
- **ROJO (R):** Riesgo alto - Revisión física obligatoria
- **NARANJA (N):** Riesgo medio - Revisión documental

---

## 🔍 Consultas Útiles

### Desde Python o cualquier cliente SQL:

```python
import duckdb

con = duckdb.connect("db/aduana.duckdb")

# Top 10 países por FOB
result = con.execute("""
    SELECT pais_origen_desc, SUM(fob_dolar) as total_fob
    FROM dw.Fact_Aduana_Item f
    JOIN dw.Dim_Pais_Origen p ON f.pais_origen_key = p.pais_origen_key
    GROUP BY pais_origen_desc
    ORDER BY total_fob DESC
    LIMIT 10
""").df()

print(result)
```

---

## 🐛 Solución de Problemas

### Error: "ModuleNotFoundError: No module named 'duckdb'"

```bash
pip install duckdb
```

### Error: "File not found: aduana_item_raw.parquet"

- Verificar que el archivo esté en `data_lake/bronze/`
- Revisar permisos de lectura

### Error: "Column not found"

- Verificar nombres de columnas en el parquet original
- Ejecutar `etl-cargar-staging.py` primero

### Base de datos corrupta

- Eliminar `db/aduana.duckdb`
- Ejecutar desde paso 1

---

## 📝 Archivos Comentados

Todos los archivos Python contienen comentarios detallados:

- **sql/crear-tablas.py** - Definición completa de schema
- **etl/etl-cargar-staging.py** - Transformaciones de datos
- **etl/etl-dimensiones.py** - Construcción de dimensiones
- **etl/etl-fact.py** - Construcción de tabla de hechos
- **olap/analitica-\*.py** - Vistas y tablas analíticas
- **graficos/graficos.py** - Generación de reportes visuales

---

## 🎯 Próximos Pasos

### Integración con Power BI

1. Exportar datos: `python helpers/exportar-parquet.py`
2. Abrir Power BI Desktop
3. Importar desde `data_lake/gold/` y `data_lake/silver/`
4. Crear modelo relacional (fact + dims)
5. Diseñar dashboards

### Análisis Avanzado

- Machine Learning: Predicción de canales de riesgo
- Clustering: Segmentación de proveedores
- Forecasting: Proyección de flujos comerciales

### Escalabilidad

- Migrar a PostgreSQL/Snowflake para datos más grandes
- Automatizar ETL con Apache Airflow
- Implementar incrementales (cargas diarias/horarias)

---

## 📚 Referencias

- **DuckDB**: https://duckdb.org/docs/
- **Star Schema**: https://en.wikipedia.org/wiki/Star_schema
- **Data Lake**: https://en.wikipedia.org/wiki/Data_lake
- **OLAP**: https://en.wikipedia.org/wiki/Online_analytical_processing

---

## 📄 Licencia

Proyecto educativo - Libre para uso y modificación

---

## ✍️ Autor

Proyecto: Data Warehouse de Comercio Exterior
Desarrollado con: Python, DuckDB, Pandas, Matplotlib
Año: 2025

---

## 📞 Soporte

Para dudas o problemas:

1. Revisar comentarios en los archivos Python
2. Ejecutar `analitica-consultas.py` para validar datos
3. Verificar estructura: `verificar-creacion-tablas.py`

---

**¡Proyecto completado y listo para análisis de datos aduanales!** 🚀
