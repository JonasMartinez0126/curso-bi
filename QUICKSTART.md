# ⚡ Quick Start - Data Warehouse Aduana

## 🎯 Inicio en 5 Minutos

### Paso 1: Instalar Python y dependencias

```bash
# Crear entorno virtual
python -m venv venv

# Activar (Windows)
venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

### Paso 2: Preparar datos

1. Colocar `aduana_item_raw.parquet` en:

   ```
   data_lake/bronze/aduana_item_raw.parquet
   ```

2. Crear carpeta de base de datos:
   ```bash
   mkdir db
   ```

### Paso 3: Ejecutar ETL (orden importante!)

```bash
# 1. Crear estructura (tablas, dimensiones, hechos)
python sql/crear-tablas.py

# 2. Cargar datos de staging (normalización)
python etl/etl-cargar-staging.py

# 3. Construir dimensiones
python etl/etl-dimensiones.py

# 4. Construir tabla de hechos
python etl/etl-fact.py

# 5. Crear tablas agregadas (OLAP)
python olap/analitica-tablas-agregadas.py

# 6. Crear vistas analíticas
python olap/analitica-vistas.py

# 7. Verificar integridad
python olap/analitica-consultas.py

# 8. Generar gráficos
python graficos/graficos.py

# 9. Exportar a parquet (Silver/Gold)
python helpers/exportar-parquet.py
```

### ✓ Resultado Final

Los gráficos estarán en:

```
data_lake/reportes_graficos/
├── 1_fob_por_operacion.png
├── 2_top_10_paises.png
├── 3_tendencia_mensual.png
├── 4_ranking_aduanas.png
├── 5_top_10_ncm.png
└── 6_canal_control.png
```

---

## 📊 Verificación Rápida

Para verificar que todo funciona:

```bash
# Ver consultas analíticas de ejemplo
python olap/analitica-consultas.py
```

Debería mostrar:

```
  R1 — FOB POR OPERACIÓN CON VARIACIÓN ANUAL
  R2 — TOP 10 PAÍSES ORIGEN (AÑO MÁS RECIENTE)
  R3 — TENDENCIA MENSUAL FOB (AÑO MÁS RECIENTE)
  ... más resultados ...
```

---

## 🗂️ Estructura de Datos Generada

```
db/aduana.duckdb          ← Base de datos principal
data_lake/
├── bronze/               ← Datos crudos
├── silver/               ← Dimensiones procesadas (.parquet)
├── gold/                 ← Tabla de hechos (.parquet)
└── reportes_graficos/    ← Gráficos PNG
```

---

## 📈 Próximo Paso: Power BI

1. Ejecutar: `python helpers/exportar-parquet.py`
2. Abrir Power BI Desktop
3. Importar archivos de `data_lake/silver/` y `data_lake/gold/`
4. Crear modelo relacional
5. Diseñar dashboards

---

## ⚠️ Errores Comunes

| Error                         | Solución                                |
| ----------------------------- | --------------------------------------- |
| `ModuleNotFoundError: duckdb` | `pip install duckdb`                    |
| `File not found: parquet`     | Colocar en `data_lake/bronze/`          |
| `Database error`              | Eliminar `db/aduana.duckdb` y reiniciar |
| `No results`                  | Verificar fecha >= 2025-01-01           |

---

## 📚 Documentación Completa

Ver `README.md` para:

- Explicación detallada de cada componente
- Esquema de base de datos
- Métricas disponibles
- Ejemplos de consultas SQL
- Troubleshooting avanzado

---

**¡Listo para análisis!** 🚀
