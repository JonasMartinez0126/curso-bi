import duckdb

DB_PATH = r"C:\curso-bi\db\aduana.duckdb"
con = duckdb.connect(DB_PATH)

print("=== DIMENSIONES FINAL ===")

try:
    con.execute("DELETE FROM dw.Dim_Regimen")
    con.execute("DELETE FROM dw.Dim_Operacion")
    con.execute("DELETE FROM dw.Dim_Pais_Destino")
    con.execute("DELETE FROM dw.Dim_Pais_Origen")
    con.execute("DELETE FROM dw.Dim_Aduana")
    con.execute("DELETE FROM dw.Dim_Producto")
    con.execute("DELETE FROM dw.Dim_Fecha")

    # OPERACION
    con.execute("""
    INSERT INTO dw.Dim_Operacion
    SELECT
        ROW_NUMBER() OVER (ORDER BY operacion) AS operacion_key,
        operacion AS tipo_operacion
    FROM (SELECT DISTINCT operacion FROM dw.stg_aduana WHERE operacion IS NOT NULL)
    """)

    # REGIMEN
    con.execute("""
    INSERT INTO dw.Dim_Regimen
    SELECT
        ROW_NUMBER() OVER (ORDER BY regimen) AS regimen_key,
        regimen AS codigo_regimen,
        regimen AS descripcion_regimen
    FROM (SELECT DISTINCT regimen FROM dw.stg_aduana WHERE regimen IS NOT NULL)
    """)

    # PAIS ORIGEN
    # El staging ya viene normalizado por etl-cargar-staging.py (macro normalizar_pais).
    # Solo se deduplicа — no se necesita normalización adicional aquí.
    con.execute("""
    INSERT INTO dw.Dim_Pais_Origen
    SELECT
        ROW_NUMBER() OVER (ORDER BY pais_origen) AS pais_origen_key,
        pais_origen AS pais_origen_desc
    FROM (SELECT DISTINCT pais_origen FROM dw.stg_aduana WHERE pais_origen IS NOT NULL)
    """)

    # PAIS DESTINO
    con.execute("""
    INSERT INTO dw.Dim_Pais_Destino
    SELECT
        ROW_NUMBER() OVER (ORDER BY pais_procedencia_destino) AS pais_destino_key,
        pais_procedencia_destino AS pais_desc_desc
    FROM (SELECT DISTINCT pais_procedencia_destino FROM dw.stg_aduana WHERE pais_procedencia_destino IS NOT NULL)
    """)

    # ADUANA
    con.execute("""
    INSERT INTO dw.Dim_Aduana
    SELECT
        ROW_NUMBER() OVER (ORDER BY aduana) AS aduana_key,
        aduana AS nombre_aduana,
        'NO ESPECIFICADO' AS ubicacion_dependencia
    FROM (SELECT DISTINCT aduana FROM dw.stg_aduana WHERE aduana IS NOT NULL)
    """)

    # PRODUCTO — agrupado por posicion arancelaria
    con.execute("""
    INSERT INTO dw.Dim_Producto
    SELECT
        ROW_NUMBER() OVER (ORDER BY posicion) AS producto_key,
        MAX(rubro)          AS rubro,
        MAX(desc_capitulo)  AS capitulo,
        MAX(desc_partida)   AS partida,
        posicion,
        MAX(desc_posicion)  AS descripcion_arancelaria
    FROM dw.stg_aduana
    WHERE posicion IS NOT NULL
    GROUP BY posicion
    """)

    # FECHA
    con.execute("""
    INSERT INTO dw.Dim_Fecha (
        fecha_key,
        fecha_oficializacion,
        anio,
        mes_numero,
        mes_nombre,
        trimestre,
        semestre
    )
    SELECT
        CAST(strftime(CAST(fecha AS DATE), '%Y%m%d') AS INTEGER) AS fecha_key,
        CAST(fecha AS DATE)                                       AS fecha_oficializacion,
        YEAR (CAST(fecha AS DATE))                                AS anio,
        MONTH(CAST(fecha AS DATE))                                AS mes_numero,
        CASE MONTH(CAST(fecha AS DATE))
            WHEN 1  THEN 'Enero'       WHEN 2  THEN 'Febrero'
            WHEN 3  THEN 'Marzo'       WHEN 4  THEN 'Abril'
            WHEN 5  THEN 'Mayo'        WHEN 6  THEN 'Junio'
            WHEN 7  THEN 'Julio'       WHEN 8  THEN 'Agosto'
            WHEN 9  THEN 'Septiembre'  WHEN 10 THEN 'Octubre'
            WHEN 11 THEN 'Noviembre'   WHEN 12 THEN 'Diciembre'
        END                                                       AS mes_nombre,
        ((MONTH(CAST(fecha AS DATE)) - 1) / 3) + 1               AS trimestre,
        CASE WHEN MONTH(CAST(fecha AS DATE)) <= 6 THEN 1 ELSE 2 END AS semestre
    FROM (
        SELECT DISTINCT oficializacion AS fecha
        FROM dw.stg_aduana
        WHERE oficializacion IS NOT NULL
    )
    """)

    # Resumen post-carga
    print()
    for tabla in ['Dim_Operacion','Dim_Regimen','Dim_Pais_Origen',
                  'Dim_Pais_Destino','Dim_Aduana','Dim_Producto','Dim_Fecha']:
        n = con.execute(f"SELECT COUNT(*) FROM dw.{tabla}").fetchone()[0]
        print(f"  {tabla:25} -> {n:>6,} registros")

    print("\nDIMENSIONES OK")

finally:
    con.close()
