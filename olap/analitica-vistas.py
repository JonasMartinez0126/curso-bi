import duckdb

DB_PATH = r"C:\curso-bi\db\aduana.duckdb"
con = duckdb.connect(DB_PATH)

print("=== CREANDO VISTAS SQL ANALÍTICAS ===\n")

sql = """
CREATE SCHEMA IF NOT EXISTS analytic;

-- ================================================================
-- MACRO GLOBAL: decodifica el código de canal a etiqueta legible
-- V -> VERDE  |  R -> ROJO  |  N -> NARANJA  |  otro -> DESCONOCIDO
-- Se aplica en todas las vistas y tablas que usan el campo canal
-- ================================================================
CREATE OR REPLACE MACRO decode_canal(c) AS (
    CASE c
        WHEN 'V' THEN 'VERDE'
        WHEN 'R' THEN 'ROJO'
        WHEN 'N' THEN 'NARANJA'
        ELSE 'DESCONOCIDO'
    END
);

-- ================================================================
-- VISTA 1: v_fob_por_operacion
-- Propósito: comparación importación vs exportación
-- Reporte: R1
-- ================================================================
DROP VIEW IF EXISTS analytic.v_fob_por_operacion;
CREATE VIEW analytic.v_fob_por_operacion AS
SELECT
    df.anio,
    df.mes_numero,
    df.mes_nombre,
    df.trimestre,
    df.semestre,
    do2.tipo_operacion,
    COUNT(*)                        AS cantidad_items,
    ROUND(SUM(f.fob_dolar),    2)   AS fob_total,
    ROUND(SUM(f.kilo_neto),    2)   AS kilo_neto_total,
    ROUND(SUM(f.flete_dolar),  2)   AS flete_total,
    ROUND(SUM(f.seguro_dolar), 2)   AS seguro_total,
    ROUND(SUM(f.total_gravamen),2)  AS gravamen_total,
    ROUND(AVG(f.fob_dolar),    2)   AS fob_promedio
FROM dw.Fact_Aduana_Item f
JOIN dw.Dim_Fecha     df  ON f.fecha_key     = df.fecha_key
JOIN dw.Dim_Operacion do2 ON f.operacion_key = do2.operacion_key
GROUP BY df.anio, df.mes_numero, df.mes_nombre,
         df.trimestre, df.semestre, do2.tipo_operacion;

-- ================================================================
-- VISTA 2: v_top_paises
-- Propósito: ranking de países por FOB, origen y destino
-- Reporte: R2
-- ================================================================
DROP VIEW IF EXISTS analytic.v_top_paises;
CREATE VIEW analytic.v_top_paises AS
SELECT
    df.anio,
    df.trimestre,
    do2.tipo_operacion,
    dpo.pais_origen_desc            AS pais,
    'ORIGEN'                        AS tipo_pais,
    COUNT(*)                        AS cantidad_items,
    ROUND(SUM(f.fob_dolar),  2)     AS fob_total,
    ROUND(SUM(f.kilo_neto),  2)     AS kilo_neto_total,
    ROUND(SUM(f.fob_dolar) * 100.0
          / SUM(SUM(f.fob_dolar)) OVER
            (PARTITION BY df.anio, do2.tipo_operacion), 2) AS pct_fob
FROM dw.Fact_Aduana_Item f
JOIN dw.Dim_Fecha       df  ON f.fecha_key        = df.fecha_key
JOIN dw.Dim_Operacion   do2 ON f.operacion_key    = do2.operacion_key
JOIN dw.Dim_Pais_Origen dpo ON f.pais_origen_key  = dpo.pais_origen_key
GROUP BY df.anio, df.trimestre, do2.tipo_operacion, dpo.pais_origen_desc

UNION ALL

SELECT
    df.anio,
    df.trimestre,
    do2.tipo_operacion,
    dpd.pais_desc_desc              AS pais,
    'DESTINO'                       AS tipo_pais,
    COUNT(*)                        AS cantidad_items,
    ROUND(SUM(f.fob_dolar),  2)     AS fob_total,
    ROUND(SUM(f.kilo_neto),  2)     AS kilo_neto_total,
    ROUND(SUM(f.fob_dolar) * 100.0
          / SUM(SUM(f.fob_dolar)) OVER
            (PARTITION BY df.anio, do2.tipo_operacion), 2) AS pct_fob
FROM dw.Fact_Aduana_Item f
JOIN dw.Dim_Fecha        df  ON f.fecha_key         = df.fecha_key
JOIN dw.Dim_Operacion    do2 ON f.operacion_key     = do2.operacion_key
JOIN dw.Dim_Pais_Destino dpd ON f.pais_destino_key  = dpd.pais_destino_key
GROUP BY df.anio, df.trimestre, do2.tipo_operacion, dpd.pais_desc_desc;

-- ================================================================
-- VISTA 3: v_tendencia_mensual
-- Propósito: evolución mes a mes con MoM y YTD
-- Reporte: R3
-- ================================================================
DROP VIEW IF EXISTS analytic.v_tendencia_mensual;
CREATE VIEW analytic.v_tendencia_mensual AS
WITH base AS (
    SELECT
        df.anio,
        df.mes_numero,
        df.mes_nombre,
        df.trimestre,
        df.semestre,
        do2.tipo_operacion,
        ROUND(SUM(f.fob_dolar),    2) AS fob_total,
        ROUND(SUM(f.kilo_neto),    2) AS kilo_neto_total,
        COUNT(*)                      AS cantidad_items,
        COUNT(DISTINCT f.pais_origen_key) AS paises_distintos
    FROM dw.Fact_Aduana_Item f
    JOIN dw.Dim_Fecha     df  ON f.fecha_key     = df.fecha_key
    JOIN dw.Dim_Operacion do2 ON f.operacion_key = do2.operacion_key
    GROUP BY df.anio, df.mes_numero, df.mes_nombre,
             df.trimestre, df.semestre, do2.tipo_operacion
)
SELECT
    *,
    ROUND(fob_total - LAG(fob_total) OVER
          (PARTITION BY tipo_operacion ORDER BY anio, mes_numero), 2) AS fob_variacion_abs,
    ROUND(
        (fob_total - LAG(fob_total) OVER
         (PARTITION BY tipo_operacion ORDER BY anio, mes_numero))
        * 100.0
        / NULLIF(LAG(fob_total) OVER
          (PARTITION BY tipo_operacion ORDER BY anio, mes_numero), 0)
    , 2)                                                               AS fob_variacion_pct,
    ROUND(SUM(fob_total) OVER
          (PARTITION BY anio, tipo_operacion ORDER BY mes_numero
           ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW), 2)      AS fob_ytd
FROM base;

-- ================================================================
-- VISTA 4: v_ranking_aduana
-- Propósito: ranking de aduanas por volumen FOB
-- Reporte: R4
-- ================================================================
DROP VIEW IF EXISTS analytic.v_ranking_aduana;
CREATE VIEW analytic.v_ranking_aduana AS
SELECT
    df.anio,
    df.trimestre,
    do2.tipo_operacion,
    da.nombre_aduana,
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
            (PARTITION BY df.anio, do2.tipo_operacion), 2) AS pct_fob
FROM dw.Fact_Aduana_Item f
JOIN dw.Dim_Fecha     df  ON f.fecha_key     = df.fecha_key
JOIN dw.Dim_Aduana    da  ON f.aduana_key    = da.aduana_key
JOIN dw.Dim_Operacion do2 ON f.operacion_key = do2.operacion_key
GROUP BY df.anio, df.trimestre, do2.tipo_operacion, da.nombre_aduana;

-- ================================================================
-- VISTA 5: v_top_ncm
-- Propósito: posiciones arancelarias con mayor FOB
-- Reporte: R5
-- ================================================================
DROP VIEW IF EXISTS analytic.v_top_ncm;
CREATE VIEW analytic.v_top_ncm AS
SELECT
    df.anio,
    df.trimestre,
    do2.tipo_operacion,
    dp.rubro,
    dp.capitulo,
    dp.posicion,
    dp.descripcion_arancelaria,
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
            (PARTITION BY df.anio, do2.tipo_operacion), 2) AS pct_fob
FROM dw.Fact_Aduana_Item f
JOIN dw.Dim_Fecha     df  ON f.fecha_key     = df.fecha_key
JOIN dw.Dim_Producto  dp  ON f.producto_key  = dp.producto_key
JOIN dw.Dim_Operacion do2 ON f.operacion_key = do2.operacion_key
GROUP BY df.anio, df.trimestre, do2.tipo_operacion,
         dp.rubro, dp.capitulo, dp.posicion, dp.descripcion_arancelaria;

-- ================================================================
-- VISTA 6: v_canal_control
-- Propósito: distribución VERDE / ROJO / NARANJA
-- Reporte: R6
-- FIX: decode_canal convierte V->VERDE, R->ROJO, N->NARANJA
-- ================================================================
DROP VIEW IF EXISTS analytic.v_canal_control;
CREATE VIEW analytic.v_canal_control AS
SELECT
    df.anio,
    df.mes_numero,
    df.mes_nombre,
    df.trimestre,
    do2.tipo_operacion,
    da.nombre_aduana,
    f.canal                         AS canal_codigo,
    decode_canal(f.canal)           AS canal_nombre,
    COUNT(*)                        AS cantidad_despachos,
    ROUND(SUM(f.fob_dolar),    2)   AS fob_total,
    ROUND(SUM(f.total_gravamen),2)  AS gravamen_total,
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
         f.canal, decode_canal(f.canal);
"""

try:
    con.execute(sql)

    vistas = [
        "analytic.v_fob_por_operacion",
        "analytic.v_top_paises",
        "analytic.v_tendencia_mensual",
        "analytic.v_ranking_aduana",
        "analytic.v_top_ncm",
        "analytic.v_canal_control",
    ]

    print(f"  {'Vista':40} {'Filas':>12}")
    print(f"  {'─'*40} {'─'*12}")
    for v in vistas:
        n = con.execute(f"SELECT COUNT(*) FROM {v}").fetchone()[0]
        print(f"  {v:40} {n:>12,}")

    # Verificar que decode_canal funciona correctamente
    print("\n--- Verificación decode_canal ---")
    df_check = con.execute("""
        SELECT canal_codigo, canal_nombre, SUM(cantidad_despachos) AS total
        FROM analytic.v_canal_control
        GROUP BY canal_codigo, canal_nombre
        ORDER BY total DESC
    """).fetchdf()
    print(df_check.to_string(index=False))

    print("\nVISTAS OK")

except Exception as e:
    print(f"Error: {e}")
finally:
    con.close()
