"""
================================================================================
ETL-CARGAR-STAGING.PY
================================================================================
Script: Ingesta y Normalización de Datos (Extract, Transform, Load)

PROPÓSITO:
  Leer datos crudos del archivo parquet original, normalizarlos y cargarlos
  en la tabla de staging (dw.stg_aduana) con transformaciones de limpieza.

FLUJO:
  1. Conectar a la base de datos DuckDB
  2. Vaciar tabla staging (DELETE FROM stg_aduana)
  3. Crear macro SQL para normalización de países (resuelve 3 problemas)
  4. Leer datos del parquet original
  5. Aplicar transformaciones:
     - Conversión de tipos (strings a DOUBLE, DATE, INTEGER)
     - Normalización de separadores decimales (coma -> punto)
     - Normalización de país (eliminar prefijos, carácteres corruptos)
     - Conversión a mayúsculas y TRIM de espacios
  6. Cargar en staging con batch_id y fecha_carga

TRANSFORMACIONES APLICADAS:

  A. NORMALIZACIÓN DE NÚMEROS:
     - El archivo fuente usa coma como separador decimal
     - Convertimos "123,45" -> 123.45 con REPLACE
     - TRY_CAST evita errores si hay valores malformados

  B. NORMALIZACIÓN DE FECHAS:
     - TRY_CAST convierte strings a DATE
     - Mantiene NULL si no puede convertir (en lugar de error)
     - Filtra solo datos de 2025 en adelante

  C. NORMALIZACIÓN DE PAÍSES (macro SQL):
     - Problema 1: Prefijos código-ISO: "BR - BRASIL" -> "BRASIL"
       Solución: REGEXP_MATCHES detecta patrón "XX - " y REGEXP_REPLACE elimina
     
     - Problema 2: Carácter corrupto: "ESPA\A" (barra invertida)
       Solución: REPLACE('\\', 'Ñ') convierte la corrupción antes de macro
     
     - Problema 3: Espacios múltiples: "ESTADOS  UNIDOS"
       Solución: REGEXP_REPLACE('\\s+', ' ') normaliza espacios

  D. NORMALIZACIÓN DE TEXTO:
     - UPPER(): Convierte a mayúsculas para consistencia
     - TRIM(): Elimina espacios al inicio y final

FILTROS APLICADOS:
  - WHERE TRY_CAST(OFICIALIZACION AS DATE) >= '2025-01-01'
    Solo datos de 2025 en adelante
  - WHERE TRY_CAST(REPLACE("FOB DOLAR", ',', '.') AS DOUBLE) > 0
    Excluye registros sin valor (FOB = 0 o NULL)

AUDITORÍA:
  - batch_id: Identificador único BATCH_YYYYMMDD_HHMMSS
    Permite trazar cuándo se cargó cada lote
  - fecha_carga: CURRENT_TIMESTAMP registra momento exacto

EJECUCIÓN:
  python etl/etl-cargar-staging.py

RESULTADO ESPERADO:
  "STAGING OK: X,XXX,XXX filas  |  batch: BATCH_20250604_153022"
================================================================================
"""

import duckdb
from datetime import datetime

# Ruta a la base de datos
DB_PATH = r"C:\curso-bi\db\aduana.duckdb"
# Ruta al archivo parquet original (datos crudos)
PARQUET_PATH = r"C:\curso-bi\data_lake\bronze\aduana_item_raw.parquet"

print("=== STAGING NORMALIZADO FINAL ===")

con = duckdb.connect(DB_PATH)

try:
    # Limpiar tabla de staging (vaciarla sin borrar estructura)
    con.execute("DELETE FROM dw.stg_aduana")

    # Generar identificador único para este lote
    batch_id = f"BATCH_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # ========================================================================
    # MACRO SQL: normalizar_pais(p)
    # ========================================================================
    # Resuelve 3 problemas detectados en auditoría:
    #   1. Prefijos código-ISO:  "BR - BRASIL" -> "BRASIL"
    #   2. Carácter corrupto:    "ESPA\A"      -> "ESPAÑA"
    #   3. Espacios múltiples:   "ESTADOS  UNIDOS" -> "ESTADOS UNIDOS"
    #
    # Lógica:
    #   REGEXP_MATCHES detecta si el país tiene patrón "XX - " (2 letras, espacio, guion)
    #   Si coincide: elimina el prefijo con REGEXP_REPLACE
    #   Si no: normaliza espacios múltiples a espacios simples
    #
    # Aplicación:
    #   normalizar_pais(REPLACE("PAIS ORIGEN", '\\', 'Ñ'))
    #   - Primero: REPLACE convierte barra invertida corrupta a Ñ
    #   - Luego: macro aplica la lógica de normalización
    # ========================================================================
    con.execute("""
    CREATE OR REPLACE MACRO normalizar_pais(p) AS (
        CASE
            -- Detecta y elimina prefijos tipo "XX - " (2 letras ISO, espacio, guion)
            WHEN REGEXP_MATCHES(UPPER(TRIM(p)), '^[A-Z]{2} - .+')
                THEN UPPER(TRIM(REGEXP_REPLACE(UPPER(TRIM(p)), '^[A-Z]{2} - ', '')))
            ELSE
                -- Normaliza espacios múltiples a espacio simple
                UPPER(TRIM(REGEXP_REPLACE(UPPER(TRIM(p)), '\\s+', ' ')))
        END
    );
    """)

    # ========================================================================
    # INSERT INTO dw.stg_aduana
    # ========================================================================
    # Lee datos del parquet, aplica transformaciones y carga en staging
    # ========================================================================
    con.execute(f"""
    INSERT INTO dw.stg_aduana (
        despacho_cifrado,
        operacion,
        destinacion,
        regimen,
        oficializacion,
        cancelacion,
        anio,
        mes,
        aduana,
        cotizacion,
        medio_transporte,
        canal,
        item,
        pais_origen,
        pais_procedencia_destino,
        uso,
        unidad_medida_estadistica,
        cantidad_estadistica,
        kilo_neto,
        kilo_bruto,
        fob_dolar,
        flete_dolar,
        seguro_dolar,
        imponible_dolar,
        imponible_gs,
        ajuste_a_incluir,
        ajuste_a_deducir,
        posicion,
        rubro,
        desc_capitulo,
        desc_partida,
        desc_posicion,
        mercaderia,
        marca_item,
        acuerdo,
        numero_subitem,
        cantidad_subitem,
        precio_unitario_subitem,
        desc_subitem,
        marca_subitem,
        derecho,
        isc,
        servicio,
        renta,
        iva,
        otros,
        total,
        batch_id
    )
    SELECT
        -- TEXTOS: normalizados a mayúsculas y sin espacios extra
        UPPER(TRIM("DESPACHO CIFRADO")),
        UPPER(TRIM(OPERACION)),
        UPPER(TRIM(DESTINACION)),
        UPPER(TRIM(REGIMEN)),

        -- FECHAS: conversión segura (TRY_CAST devuelve NULL si falla)
        TRY_CAST(OFICIALIZACION AS DATE),
        CANCELACION,
        TRY_CAST("AÑO" AS INTEGER),
        MES,

        -- TEXTOS: normalización
        UPPER(TRIM(ADUANA)),
        TRY_CAST(REPLACE(COTIZACION, ',', '.') AS DOUBLE),

        UPPER(TRIM("MEDIO TRANSPORTE")),
        UPPER(TRIM(CANAL)),

        -- NÚMEROS: conversión de integer
        TRY_CAST(ITEM AS INTEGER),

        -- PAÍSES: normalización con macro
        -- REPLACE('\\', 'Ñ') arregla caracteres corruptos antes
        normalizar_pais(REPLACE("PAIS ORIGEN",              '\\', 'Ñ')),
        normalizar_pais(REPLACE("PAIS PROCEDENCIA/DESTINO", '\\', 'Ñ')),

        UPPER(TRIM(USO)),
        UPPER(TRIM("UNIDAD MEDIDA ESTADISTICA")),

        -- NÚMEROS: conversión de DOUBLE (coma -> punto)
        TRY_CAST(REPLACE("CANTIDAD ESTADISTICA",    ',', '.') AS DOUBLE),
        TRY_CAST(REPLACE("KILO NETO",               ',', '.') AS DOUBLE),
        TRY_CAST(REPLACE("KILO BRUTO",              ',', '.') AS DOUBLE),

        -- VALORES MONETARIOS: conversión de USD (coma -> punto)
        TRY_CAST(REPLACE("FOB DOLAR",               ',', '.') AS DOUBLE),
        TRY_CAST(REPLACE("FLETE DOLAR",             ',', '.') AS DOUBLE),
        TRY_CAST(REPLACE("SEGURO DOLAR",            ',', '.') AS DOUBLE),

        -- BASES IMPONIBLES: conversión
        TRY_CAST(REPLACE("IMPONIBLE DOLAR",         ',', '.') AS DOUBLE),
        TRY_CAST(REPLACE("IMPONIBLE GS",            ',', '.') AS DOUBLE),

        -- AJUSTES: conversión
        TRY_CAST(REPLACE("AJUSTE A INCLUIR",        ',', '.') AS DOUBLE),
        TRY_CAST(REPLACE("AJUSTE A DEDUCIR",        ',', '.') AS DOUBLE),

        -- POSICIONES ARANCELARIAS: texto normalizado
        UPPER(TRIM(POSICION)),
        UPPER(TRIM(RUBRO)),
        UPPER(TRIM("DESC CAPITULO")),
        UPPER(TRIM("DESC PARTIDA")),
        UPPER(TRIM("DESC POSICION")),
        UPPER(TRIM(MERCADERIA)),
        UPPER(TRIM("MARCA ITEM")),
        UPPER(TRIM(ACUERDO)),

        -- SUBITEMS: conversión numérica
        TRY_CAST("NUMERO SUBITEM"                          AS INTEGER),
        TRY_CAST("CANTIDAD SUBITEM"                        AS DOUBLE),
        TRY_CAST(REPLACE("PRECION UNITARIO SUBITEM", ',', '.') AS DOUBLE),

        UPPER(TRIM("DESC SUBITEM")),
        UPPER(TRIM("MARCA SUBITEM")),

        -- GRAVÁMENES: conversión de USD (coma -> punto)
        TRY_CAST(REPLACE(DERECHO,   ',', '.') AS DOUBLE),
        TRY_CAST(REPLACE(ISC,       ',', '.') AS DOUBLE),
        TRY_CAST(REPLACE(SERVICIO,  ',', '.') AS DOUBLE),
        TRY_CAST(REPLACE(RENTA,     ',', '.') AS DOUBLE),
        TRY_CAST(REPLACE(IVA,       ',', '.') AS DOUBLE),
        TRY_CAST(REPLACE(OTROS,     ',', '.') AS DOUBLE),
        TRY_CAST(REPLACE(TOTAL,     ',', '.') AS DOUBLE),

        -- AUDITORÍA
        '{batch_id}'
    FROM read_parquet('{PARQUET_PATH}')
    WHERE TRY_CAST(OFICIALIZACION AS DATE) >= '2025-01-01'
      AND TRY_CAST(REPLACE("FOB DOLAR", ',', '.') AS DOUBLE) > 0
    """)

    # Obtener recuento de filas cargadas
    total = con.execute("SELECT COUNT(*) FROM dw.stg_aduana").fetchone()[0]
    print(f"STAGING OK: {total:,} filas  |  batch: {batch_id}")


finally:
    con.close()
