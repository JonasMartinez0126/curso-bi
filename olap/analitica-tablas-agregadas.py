import duckdb

DB_PATH = r"C:\curso-bi\db\aduana.duckdb"
con = duckdb.connect(DB_PATH)

print("=== CREANDO TABLAS AGREGADAS ===\n")

sql = """
CREATE SCHEMA IF NOT EXISTS analytic;

-- Aseguramos que la macro decode_canal esté disponible
-- (se crea en analitica-vistas.py, la redefinimos aquí por si se corre solo)
CREATE OR REPLACE MACRO decode_canal(c) AS (
    CASE c
        WHEN 'V' THEN 'VERDE'
        WHEN 'R' THEN 'ROJO'
        WHEN 'N' THEN 'NARANJA'
        ELSE 'DESCONOCIDO'
    END
);

-- ================================================================
-- TABLA AGREGADA 1: agg_fob_mensual_operacion
-- Grano: año + mes + tipo_operacion
-- Uso: R1, R3
-- ================================================================
DROP TABLE IF EXISTS analytic.agg_fob_mensual_operacion;
CREATE TABLE analytic.agg_fob_mensual_operacion AS
SELECT
    df.anio, df.mes_numero, df.mes_nombre,
    df.trimestre, df.semestre,
    do2.tipo_operacion,
    COUNT(*)                        AS cantidad_items,
    ROUND(SUM(f.fob_dolar),    2)   AS fob_total,
    ROUND(SUM(f.kilo_neto),    2)   AS kilo_neto_total,
    ROUND(SUM(f.flete_dolar),  2)   AS flete_total,
    ROUND(SUM(f.seguro_dolar), 2)   AS seguro_total,
    ROUND(SUM(f.derecho),      2)   AS derecho_total,
    ROUND(SUM(f.isc),          2)   AS isc_total,
    ROUND(SUM(f.iva),          2)   AS iva_total,
    ROUND(SUM(f.total_gravamen),2)  AS gravamen_total,
    ROUND(AVG(f.fob_dolar),    2)   AS fob_promedio,
    ROUND(MIN(f.fob_dolar),    2)   AS fob_minimo,
    ROUND(MAX(f.fob_dolar),    2)   AS fob_maximo
FROM dw.Fact_Aduana_Item f
JOIN dw.Dim_Fecha     df  ON f.fecha_key     = df.fecha_key
JOIN dw.Dim_Operacion do2 ON f.operacion_key = do2.operacion_key
GROUP BY df.anio, df.mes_numero, df.mes_nombre,
         df.trimestre, df.semestre, do2.tipo_operacion
ORDER BY df.anio, df.mes_numero, do2.tipo_operacion;

-- ================================================================
-- TABLA AGREGADA 2: agg_fob_pais_anual
-- Grano: año + trimestre + pais_origen + pais_destino + tipo_operacion
-- Uso: R2
-- ================================================================
DROP TABLE IF EXISTS analytic.agg_fob_pais_anual;
CREATE TABLE analytic.agg_fob_pais_anual AS
SELECT
    df.anio, df.trimestre,
    do2.tipo_operacion,
    dpo.pais_origen_desc,
    dpd.pais_desc_desc                      AS pais_destino_desc,
    COUNT(*)                                AS cantidad_items,
    ROUND(SUM(f.fob_dolar),  2)             AS fob_total,
    ROUND(SUM(f.kilo_neto),  2)             AS kilo_neto_total,
    ROUND(AVG(f.fob_dolar),  2)             AS fob_promedio,
    ROUND(SUM(f.fob_dolar) * 100.0
          / SUM(SUM(f.fob_dolar)) OVER
            (PARTITION BY df.anio, do2.tipo_operacion), 4) AS pct_fob_sobre_total
FROM dw.Fact_Aduana_Item f
JOIN dw.Dim_Fecha        df  ON f.fecha_key        = df.fecha_key
JOIN dw.Dim_Operacion    do2 ON f.operacion_key    = do2.operacion_key
JOIN dw.Dim_Pais_Origen  dpo ON f.pais_origen_key  = dpo.pais_origen_key
JOIN dw.Dim_Pais_Destino dpd ON f.pais_destino_key = dpd.pais_destino_key
GROUP BY df.anio, df.trimestre, do2.tipo_operacion,
         dpo.pais_origen_desc, dpd.pais_desc_desc
ORDER BY df.anio, do2.tipo_operacion, fob_total DESC;

-- ================================================================
-- TABLA AGREGADA 3: agg_fob_aduana_mensual
-- Grano: año + mes + aduana + tipo_operacion
-- Uso: R4
-- ================================================================
DROP TABLE IF EXISTS analytic.agg_fob_aduana_mensual;
CREATE TABLE analytic.agg_fob_aduana_mensual AS
SELECT
    df.anio, df.mes_numero, df.mes_nombre,
    df.trimestre, do2.tipo_operacion,
    da.nombre_aduana,
    COUNT(*)                     AS cantidad_items,
    ROUND(SUM(f.fob_dolar),  2)  AS fob_total,
    ROUND(SUM(f.kilo_neto),  2)  AS kilo_neto_total,
    ROUND(AVG(f.fob_dolar),  2)  AS fob_promedio,
    ROUND(SUM(f.total_gravamen),2) AS gravamen_total,
    RANK() OVER (
        PARTITION BY df.anio, df.mes_numero, do2.tipo_operacion
        ORDER BY SUM(f.fob_dolar) DESC
    )                            AS rank_fob_mes,
    ROUND(SUM(f.fob_dolar) * 100.0
          / SUM(SUM(f.fob_dolar)) OVER
            (PARTITION BY df.anio, df.mes_numero, do2.tipo_operacion), 2) AS pct_fob
FROM dw.Fact_Aduana_Item f
JOIN dw.Dim_Fecha     df  ON f.fecha_key     = df.fecha_key
JOIN dw.Dim_Aduana    da  ON f.aduana_key    = da.aduana_key
JOIN dw.Dim_Operacion do2 ON f.operacion_key = do2.operacion_key
GROUP BY df.anio, df.mes_numero, df.mes_nombre,
         df.trimestre, do2.tipo_operacion, da.nombre_aduana
ORDER BY df.anio, df.mes_numero, do2.tipo_operacion, fob_total DESC;

-- ================================================================
-- TABLA AGREGADA 4: agg_fob_ncm_anual
-- Grano: año + trimestre + ncm + tipo_operacion
-- Uso: R5
-- ================================================================
DROP TABLE IF EXISTS analytic.agg_fob_ncm_anual;
CREATE TABLE analytic.agg_fob_ncm_anual AS
SELECT
    df.anio, df.trimestre,
    do2.tipo_operacion,
    dp.rubro, dp.capitulo,
    dp.posicion, dp.descripcion_arancelaria,
    COUNT(*)                    AS cantidad_items,
    ROUND(SUM(f.fob_dolar), 2)  AS fob_total,
    ROUND(SUM(f.kilo_neto), 2)  AS kilo_neto_total,
    ROUND(AVG(f.fob_dolar), 2)  AS fob_promedio,
    RANK() OVER (
        PARTITION BY df.anio, do2.tipo_operacion
        ORDER BY SUM(f.fob_dolar) DESC
    )                           AS rank_fob,
    ROUND(SUM(f.fob_dolar) * 100.0
          / SUM(SUM(f.fob_dolar)) OVER
            (PARTITION BY df.anio, do2.tipo_operacion), 4) AS pct_fob
FROM dw.Fact_Aduana_Item f
JOIN dw.Dim_Fecha     df  ON f.fecha_key     = df.fecha_key
JOIN dw.Dim_Producto  dp  ON f.producto_key  = dp.producto_key
JOIN dw.Dim_Operacion do2 ON f.operacion_key = do2.operacion_key
GROUP BY df.anio, df.trimestre, do2.tipo_operacion,
         dp.rubro, dp.capitulo, dp.posicion, dp.descripcion_arancelaria
ORDER BY df.anio, do2.tipo_operacion, fob_total DESC;

-- ================================================================
-- TABLA AGREGADA 5: agg_canal_mensual
-- Grano: año + mes + aduana + canal
-- Uso: R6
-- FIX: canal_codigo (V/R/N) + canal_nombre (VERDE/ROJO/NARANJA)
-- ================================================================
DROP TABLE IF EXISTS analytic.agg_canal_mensual;
CREATE TABLE analytic.agg_canal_mensual AS
SELECT
    df.anio, df.mes_numero, df.mes_nombre,
    df.trimestre, do2.tipo_operacion,
    da.nombre_aduana,
    f.canal                        AS canal_codigo,
    decode_canal(f.canal)          AS canal_nombre,
    COUNT(*)                       AS cantidad_despachos,
    ROUND(SUM(f.fob_dolar),    2)  AS fob_total,
    ROUND(SUM(f.total_gravamen),2) AS gravamen_total,
    ROUND(AVG(f.fob_dolar),    2)  AS fob_promedio,
    ROUND(COUNT(*) * 100.0
          / SUM(COUNT(*)) OVER
            (PARTITION BY df.anio, df.mes_numero,
             do2.tipo_operacion, da.nombre_aduana), 2) AS pct_canal
FROM dw.Fact_Aduana_Item f
JOIN dw.Dim_Fecha     df  ON f.fecha_key     = df.fecha_key
JOIN dw.Dim_Operacion do2 ON f.operacion_key = do2.operacion_key
JOIN dw.Dim_Aduana    da  ON f.aduana_key    = da.aduana_key
WHERE f.canal IS NOT NULL
GROUP BY df.anio, df.mes_numero, df.mes_nombre, df.trimestre,
         do2.tipo_operacion, da.nombre_aduana,
         f.canal, decode_canal(f.canal)
ORDER BY df.anio, df.mes_numero, da.nombre_aduana, f.canal;
"""

try:
    con.execute(sql)

    tablas = [
        ("analytic.agg_fob_mensual_operacion", "año + mes + operacion"),
        ("analytic.agg_fob_pais_anual",        "año + trimestre + pais + operacion"),
        ("analytic.agg_fob_aduana_mensual",    "año + mes + aduana + operacion"),
        ("analytic.agg_fob_ncm_anual",         "año + trimestre + ncm + operacion"),
        ("analytic.agg_canal_mensual",         "año + mes + aduana + canal"),
    ]

    print(f"  {'Tabla':45} {'Filas':>10}  {'Grano':35}")
    print(f"  {'─'*45} {'─'*10}  {'─'*35}")
    for tabla, grano in tablas:
        n = con.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
        print(f"  {tabla:45} {n:>10,}  {grano}")

    # Verificar decode_canal en la tabla de canal
    print("\n--- Verificación canal en agg_canal_mensual ---")
    df_check = con.execute("""
        SELECT canal_codigo, canal_nombre,
               SUM(cantidad_despachos) AS total_despachos,
               ROUND(SUM(fob_total)/1e6, 1) AS fob_millones
        FROM analytic.agg_canal_mensual
        GROUP BY canal_codigo, canal_nombre
        ORDER BY total_despachos DESC
    """).fetchdf()
    print(df_check.to_string(index=False))

    print("\nTABLAS AGREGADAS OK")

except Exception as e:
    print(f"Error: {e}")
finally:
    con.close()
