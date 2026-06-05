# 📚 Índice de Documentación del Proyecto

## 🎯 Acceso Rápido

### Para Empezar Rápido

- 📖 **[QUICKSTART.md](QUICKSTART.md)** - Inicia en 5 minutos

### Documentación Completa

- 📖 **[README.md](README.md)** - Guía completa del proyecto

### Configuración

- 📦 **[requirements.txt](requirements.txt)** - Dependencias Python

---

## 📂 Estructura de Archivos Python

### SQL & Base de Datos

```
sql/
├── crear-tablas.py                   ← CREAR ESTRUCTURA DW
│   ├─ Crea schema 'dw'
│   ├─ 7 dimensiones
│   └─ Tabla de hechos (Star Schema)
│
└── verificar-creacion-tablas.py      ← VALIDAR INTEGRIDAD
    └─ Pruebas de tablas creadas
```

### ETL (Extract, Transform, Load)

```
etl/
├── etl-cargar-staging.py             ← INGESTA & NORMALIZACIÓN
│   ├─ Lee parquet original
│   ├─ Convierte tipos (comillas decimales, fechas, etc)
│   ├─ Normaliza países (prefijos, caracteres corruptos)
│   └─ Carga en dw.stg_aduana
│
├── etl-dimensiones.py                ← CONSTRUIR DIMENSIONES
│   ├─ Deduplica valores
│   ├─ Asigna claves numéricas (surrogate keys)
│   └─ Llena 7 tablas Dim_*
│
└── etl-fact.py                       ← CONSTRUIR TABLA DE HECHOS
    ├─ Busca claves en dimensiones
    ├─ Calcula métricas (FOB, gravámenes, etc)
    └─ Llena dw.Fact_Aduana_Item (millones de filas)
```

### OLAP (Análisis Online Analytic Processing)

```
olap/
├── analitica-vistas.py               ← CREAR VISTAS SQL
│   ├─ v_fob_por_operacion
│   ├─ v_top_paises
│   ├─ v_tendencia_mensual
│   ├─ v_ranking_aduana
│   ├─ v_top_ncm
│   └─ v_canal_control
│
├── analitica-tablas-agregadas.py     ← PRECOMPUTAR AGREGACIONES
│   ├─ agg_fob_mensual_operacion
│   ├─ agg_fob_pais_anual
│   ├─ agg_fob_aduana_mensual
│   ├─ agg_fob_ncm_anual
│   └─ agg_canal_mensual
│
└── analitica-consultas.py            ← EJEMPLOS DE QUERIES
    ├─ R1: FOB por operación (YoY)
    ├─ R2: Top 10 países
    ├─ R3: Tendencia mensual
    ├─ R4: Ranking aduanas
    ├─ R5: Top 10 NCM
    ├─ R6: Canales de control
    └─ BONUS: Análisis de riesgo
```

### Reportes Gráficos

```
graficos/
└── graficos.py                       ← GENERAR PNG (300 DPI)
    ├─ 1_fob_por_operacion.png (línea - tendencia)
    ├─ 2_top_10_paises.png (barras - socios)
    ├─ 3_tendencia_mensual.png (línea - YTD)
    ├─ 4_ranking_aduanas.png (barras - por operación)
    ├─ 5_top_10_ncm.png (barras - productos top)
    └─ 6_canal_control.png (barras apiladas - riesgo)
```

### Helpers

```
helpers/
├── export-parquet-bronze.py          ← IMPORTAR A BRONZE
│   └─ Carga datos al data lake
│
└── exportar-parquet.py               ← EXPORTAR SILVER/GOLD
    ├─ Dimensiones → data_lake/silver/
    └─ Hechos → data_lake/gold/
```

---

## 🔄 Orden de Ejecución

```
1️⃣  python sql/crear-tablas.py
    └─ Crea estructura (tablas vacías)

2️⃣  python etl/etl-cargar-staging.py
    └─ Carga datos del parquet original

3️⃣  python etl/etl-dimensiones.py
    └─ Construye 7 dimensiones

4️⃣  python etl/etl-fact.py
    └─ Construye tabla de hechos

5️⃣  python olap/analitica-tablas-agregadas.py
    └─ Precomputa agregaciones

6️⃣  python olap/analitica-vistas.py
    └─ Crea vistas analíticas

7️⃣  python olap/analitica-consultas.py
    └─ Valida integridad

8️⃣  python graficos/graficos.py
    └─ Genera 6 reportes PNG

9️⃣  python helpers/exportar-parquet.py
    └─ Exporta a Silver/Gold para Power BI
```

---

## 📊 Esquema Simplificado

```
DIMENSIONES (Silver)        TABLA DE HECHOS (Gold)

Dim_Fecha ─┐               Fact_Aduana_Item
Dim_Aduana ├────────────→  ├─ Métricas (FOB, fletes, gravámenes)
Dim_Producto               ├─ Pesos (neto, bruto)
Dim_Pais_Origen ├─ keys ──→ ├─ Auditoría (canal, batch, fecha)
Dim_Pais_Destino          └─ 8 claves foráneas a dimensiones
Dim_Operacion
Dim_Regimen

→ Modelo Estrella optimizado para OLAP
→ 1 tabla de hechos grande + 7 dimensiones pequeñas
→ Queries muy rápidas de análisis
```

---

## 📈 Métricas Principales

| Métrica            | Unidad | Significado                           |
| ------------------ | ------ | ------------------------------------- |
| **FOB**            | USD    | Valor de mercancía (base del arancel) |
| **Flete**          | USD    | Costo de transporte                   |
| **Seguro**         | USD    | Costo de seguro                       |
| **Derecho**        | USD    | Arancel aduanal                       |
| **IVA**            | USD    | Impuesto al Valor Agregado            |
| **Total Gravamen** | USD    | Suma de todos los impuestos           |
| **Kilo Neto**      | kg     | Peso sin envase                       |
| **Kilo Bruto**     | kg     | Peso total con envase                 |

---

## 🎯 Consulta Rápida Desde Python

```python
import duckdb

con = duckdb.connect("db/aduana.duckdb")

# Ejemplo 1: Top países
df = con.execute("""
    SELECT pais_origen_desc, SUM(fob_dolar) as total
    FROM dw.Fact_Aduana_Item f
    JOIN dw.Dim_Pais_Origen p
      ON f.pais_origen_key = p.pais_origen_key
    GROUP BY pais_origen_desc
    ORDER BY total DESC
    LIMIT 10
""").df()

# Ejemplo 2: FOB por mes
df = con.execute("""
    SELECT fecha_key, SUM(fob_dolar) as total
    FROM analytic.agg_fob_mensual_operacion
    GROUP BY fecha_key
    ORDER BY fecha_key
""").df()

con.close()
```

---

## 🐛 Troubleshooting

| Problema                      | Solución                                              |
| ----------------------------- | ----------------------------------------------------- |
| `ModuleNotFoundError: duckdb` | `pip install -r requirements.txt`                     |
| `File not found: parquet`     | Colocar en `data_lake/bronze/aduana_item_raw.parquet` |
| `Database locked`             | Cerrar otras conexiones o eliminar DB                 |
| `0 filas`                     | Verificar fechas >= 2025-01-01 y FOB > 0              |

---

## 📚 Archivos Comentados Detalladamente

Todos los archivos Python incluyen:

- ✓ Docstring al inicio explicando propósito
- ✓ Comentarios en bloques SQL
- ✓ Explicación de transformaciones
- ✓ Documentación de filtros y validaciones
- ✓ Instrucciones de ejecución

---

## 🚀 Próximos Pasos Sugeridos

1. **Power BI**
   - Exportar datos: `python helpers/exportar-parquet.py`
   - Importar en Power BI Desktop desde `data_lake/gold/` y `data_lake/silver/`
   - Crear dashboards interactivos

2. **Machine Learning**
   - Predicción de canales de riesgo (VERDE/ROJO)
   - Clustering de proveedores
   - Forecasting de flujos comerciales

3. **Automatización**
   - Apache Airflow para ETL programado
   - Carga incremental diaria
   - Alertas por anomalías

4. **Escalabilidad**
   - Migrar a PostgreSQL para volúmenes mayores
   - Usar Snowflake para datos masivos
   - Implementar datalake distribuido (S3 + Spark)

---

## 📞 Referencia Rápida

| Componente | Archivo                       | Propósito             |
| ---------- | ----------------------------- | --------------------- |
| Estructura | `sql/crear-tablas.py`         | Crear tablas DW       |
| Ingesta    | `etl/etl-cargar-staging.py`   | Cargar datos crudos   |
| Dims       | `etl/etl-dimensiones.py`      | Construir dimensiones |
| Hechos     | `etl/etl-fact.py`             | Construir hechos      |
| OLAP       | `olap/analitica-*.py`         | Vistas y agregaciones |
| Gráficos   | `graficos/graficos.py`        | Reportes visuales     |
| Exporta    | `helpers/exportar-parquet.py` | Sacar a Silver/Gold   |

---

**¡Documentación completa y lista para consulta!** 📖
