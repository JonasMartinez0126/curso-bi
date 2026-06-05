import duckdb
import pandas as pd

DB_PATH = r"C:\curso-bi\db\aduana.duckdb"
con = duckdb.connect(DB_PATH)

pd.set_option("display.float_format", lambda x: f"{x:,.2f}")
pd.set_option("display.max_columns", 20)
pd.set_option("display.width", 120)

def run(titulo, sql, limite=15):
    print(f"\n{'='*65}")
    print(f"  {titulo}")
    print(f"{'='*65}")
    try:
        df = con.execute(sql).fetchdf()
        if df.empty:
            print("  Sin resultados.")
        else:
            print(df.head(limite).to_string(index=False))
            if len(df) > limite:
                print(f"  ... ({len(df):,} filas totales, mostrando {limite})")
    except Exception as e:
        print(f"  Error: {e}")

print("\n" + "="*65)
print("   CONSULTAS ANALÍTICAS — DATA WAREHOUSE ADUANA 2025")
print("="*65)

# ================================================================
# CONSULTA 1: FOB por operación con variación anual (YoY)
# ================================================================
run("R1 — FOB POR OPERACIÓN CON VARIACIÓN ANUAL", """
SELECT
    tipo_operacion,
    anio,
    SUM(fob_total)              AS fob_anual,
    SUM(cantidad_items)         AS items_totales,
    ROUND(AVG(fob_promedio), 2) AS ticket_promedio,
    LAG(SUM(fob_total)) OVER (
        PARTITION BY tipo_operacion ORDER BY anio
    )                           AS fob_anio_anterior,
    ROUND(
        (SUM(fob_total) - LAG(SUM(fob_total)) OVER (
            PARTITION BY tipo_operacion ORDER BY anio
        )) * 100.0
        / NULLIF(LAG(SUM(fob_total)) OVER (
            PARTITION BY tipo_operacion ORDER BY anio
        ), 0)
    , 2)                        AS variacion_pct_yoy
FROM analytic.agg_fob_mensual_operacion
GROUP BY tipo_operacion, anio
ORDER BY tipo_operacion, anio
""")

# ================================================================
# CONSULTA 2: Top 10 países origen — año más reciente
# ================================================================
run("R2 — TOP 10 PAÍSES ORIGEN (AÑO MÁS RECIENTE)", """
WITH anio_max AS (
    SELECT MAX(anio) AS anio FROM analytic.agg_fob_pais_anual
)
SELECT
    a.pais_origen_desc,
    SUM(a.fob_total)                        AS fob_total,
    SUM(a.cantidad_items)                   AS items,
    ROUND(SUM(a.pct_fob_sobre_total), 2)    AS pct_del_total,
    RANK() OVER (ORDER BY SUM(a.fob_total) DESC) AS ranking
FROM analytic.agg_fob_pais_anual a
JOIN anio_max m ON a.anio = m.anio
GROUP BY a.pais_origen_desc
ORDER BY fob_total DESC
LIMIT 10
""")

# ================================================================
# CONSULTA 3: Tendencia mensual con MoM y YTD
# ================================================================
run("R3 — TENDENCIA MENSUAL FOB (AÑO MÁS RECIENTE)", """
WITH anio_max AS (
    SELECT MAX(anio) AS anio FROM analytic.agg_fob_mensual_operacion
)
SELECT
    a.mes_numero,
    a.mes_nombre,
    a.tipo_operacion,
    a.fob_total,
    a.fob_variacion_abs,
    a.fob_variacion_pct     AS mom_pct,
    a.fob_ytd,
    a.cantidad_items
FROM analytic.v_tendencia_mensual a
JOIN anio_max m ON a.anio = m.anio
ORDER BY a.tipo_operacion, a.mes_numero
""")

# ================================================================
# CONSULTA 4: Ranking de aduanas — año más reciente
# ================================================================
run("R4 — RANKING ADUANAS POR FOB (AÑO MÁS RECIENTE)", """
WITH anio_max AS (
    SELECT MAX(anio) AS anio FROM analytic.agg_fob_aduana_mensual
)
SELECT
    a.nombre_aduana,
    a.tipo_operacion,
    SUM(a.fob_total)            AS fob_anual,
    SUM(a.cantidad_items)       AS items_totales,
    ROUND(AVG(a.fob_promedio), 2) AS ticket_promedio,
    ROUND(SUM(a.pct_fob), 2)   AS pct_participacion,
    RANK() OVER (
        PARTITION BY a.tipo_operacion
        ORDER BY SUM(a.fob_total) DESC
    )                           AS ranking
FROM analytic.agg_fob_aduana_mensual a
JOIN anio_max m ON a.anio = m.anio
GROUP BY a.nombre_aduana, a.tipo_operacion
ORDER BY a.tipo_operacion, fob_anual DESC
""")

# ================================================================
# CONSULTA 5: Top 10 NCM — año más reciente
# ================================================================
run("R5 — TOP 10 NCM POR FOB (AÑO MÁS RECIENTE)", """
WITH anio_max AS (
    SELECT MAX(anio) AS anio FROM analytic.agg_fob_ncm_anual
)
SELECT
    a.posicion,
    LEFT(a.descripcion_arancelaria, 45)   AS descripcion,
    a.rubro,
    a.tipo_operacion,
    a.fob_total,
    a.cantidad_items,
    a.pct_fob,
    a.rank_fob                            AS ranking
FROM analytic.agg_fob_ncm_anual a
JOIN anio_max m ON a.anio = m.anio
WHERE a.rank_fob <= 10
ORDER BY a.tipo_operacion, a.rank_fob
""")

# ================================================================
# CONSULTA 6: Canal de control — año más reciente
# FIX: usa canal_nombre (VERDE/ROJO/NARANJA) en vez de V/R/N
# ================================================================
run("R6 — CANAL DE CONTROL (AÑO MÁS RECIENTE)", """
WITH anio_max AS (
    SELECT MAX(anio) AS anio FROM analytic.agg_canal_mensual
)
SELECT
    a.canal_codigo,
    a.canal_nombre,
    a.tipo_operacion,
    SUM(a.cantidad_despachos)           AS total_despachos,
    ROUND(SUM(a.fob_total) / 1e6, 2)   AS fob_millones,
    ROUND(SUM(a.gravamen_total) / 1e6, 2) AS gravamen_millones,
    ROUND(
        SUM(a.cantidad_despachos) * 100.0
        / SUM(SUM(a.cantidad_despachos)) OVER (
            PARTITION BY a.tipo_operacion
        ), 2
    )                                   AS pct_del_total
FROM analytic.agg_canal_mensual a
JOIN anio_max m ON a.anio = m.anio
GROUP BY a.canal_codigo, a.canal_nombre, a.tipo_operacion
ORDER BY a.tipo_operacion, total_despachos DESC
""")

# ================================================================
# CONSULTA 7 (BONUS): Países con mayor proporción canal ROJO
# FIX: filtra por canal_nombre = 'ROJO' en vez de canal = 'ROJO'
# ================================================================
run("BONUS — PAÍSES CON MAYOR PROPORCIÓN CANAL ROJO", """
WITH anio_max AS (
    SELECT MAX(anio) AS anio FROM analytic.agg_fob_pais_anual
),
canal_pais AS (
    SELECT
        dpo.pais_origen_desc,
        f.canal                     AS canal_codigo,
        decode_canal(f.canal)       AS canal_nombre,
        COUNT(*)                    AS despachos,
        ROUND(SUM(f.fob_dolar)/1e6, 2) AS fob_millones
    FROM dw.Fact_Aduana_Item f
    JOIN dw.Dim_Fecha       df  ON f.fecha_key       = df.fecha_key
    JOIN dw.Dim_Pais_Origen dpo ON f.pais_origen_key = dpo.pais_origen_key
    JOIN anio_max m              ON df.anio           = m.anio
    WHERE f.canal IS NOT NULL
    GROUP BY dpo.pais_origen_desc, f.canal, decode_canal(f.canal)
),
totales AS (
    SELECT pais_origen_desc, SUM(despachos) AS total
    FROM canal_pais GROUP BY 1
)
SELECT
    cp.pais_origen_desc,
    cp.despachos                                AS despachos_rojos,
    t.total                                     AS despachos_totales,
    ROUND(cp.despachos * 100.0 / t.total, 1)   AS pct_rojo,
    cp.fob_millones                             AS fob_rojo_millones
FROM canal_pais cp
JOIN totales t ON cp.pais_origen_desc = t.pais_origen_desc
WHERE cp.canal_nombre = 'ROJO'
  AND t.total >= 100
ORDER BY pct_rojo DESC
LIMIT 10
""")

con.close()
print("\n" + "="*65)
print("   CONSULTAS ANALÍTICAS COMPLETADAS")
print("="*65)
