import duckdb

DB_PATH = r"C:\curso-bi\db\aduana.duckdb"

con = duckdb.connect(DB_PATH)

print("=== FACT FINAL ===")

try:
    con.execute("DELETE FROM dw.Fact_Aduana_Item")

    con.execute("""
    INSERT INTO dw.Fact_Aduana_Item (
        id_fact_key,
        fecha_key,
        aduana_key,
        producto_key,
        pais_origen_key,
        pais_destino_key,
        operacion_key,
        regimen_key,
        kilo_neto,
        kilo_bruto,
        fob_dolar,
        flete_dolar,
        seguro_dolar,
        derecho,
        isc,
        iva,
        total_gravamen,
        valor_fob_subitem,
        kilo_neto_subitem,
        canal,
        batch_id,
        fecha_carga
    )
    SELECT
        ROW_NUMBER() OVER ()                               AS id_fact_key,

        d_f.fecha_key,
        d_a.aduana_key,
        d_p.producto_key,

        -- JOIN directo: el staging ya viene normalizado por etl-cargar-staging.py
        -- La macro normalizar_pais garantiza que staging == dim en todos los casos
        d_po.pais_origen_key,
        d_pd.pais_destino_key,

        d_o.operacion_key,
        d_r.regimen_key,

        stg.kilo_neto,
        stg.kilo_bruto,
        stg.fob_dolar,
        stg.flete_dolar,
        stg.seguro_dolar,
        stg.derecho,
        stg.isc,
        stg.iva,
        stg.total                                          AS total_gravamen,
        (stg.precio_unitario_subitem * stg.cantidad_subitem) AS valor_fob_subitem,
        stg.cantidad_subitem                               AS kilo_neto_subitem,
        stg.canal,
        stg.batch_id,
        CURRENT_TIMESTAMP

    FROM dw.stg_aduana stg

    LEFT JOIN dw.Dim_Fecha d_f
        ON stg.oficializacion = d_f.fecha_oficializacion

    LEFT JOIN dw.Dim_Aduana d_a
        ON stg.aduana = d_a.nombre_aduana

    LEFT JOIN dw.Dim_Producto d_p
        ON stg.posicion = d_p.posicion

    LEFT JOIN dw.Dim_Pais_Origen d_po
        ON stg.pais_origen = d_po.pais_origen_desc

    LEFT JOIN dw.Dim_Pais_Destino d_pd
        ON stg.pais_procedencia_destino = d_pd.pais_desc_desc

    LEFT JOIN dw.Dim_Operacion d_o
        ON stg.operacion = d_o.tipo_operacion

    LEFT JOIN dw.Dim_Regimen d_r
        ON stg.regimen = d_r.codigo_regimen
    """)

    total    = con.execute("SELECT COUNT(*) FROM dw.Fact_Aduana_Item").fetchone()[0]
    null_po  = con.execute("SELECT COUNT(*) FROM dw.Fact_Aduana_Item WHERE pais_origen_key  IS NULL").fetchone()[0]
    null_pd  = con.execute("SELECT COUNT(*) FROM dw.Fact_Aduana_Item WHERE pais_destino_key IS NULL").fetchone()[0]
    null_adu = con.execute("SELECT COUNT(*) FROM dw.Fact_Aduana_Item WHERE aduana_key        IS NULL").fetchone()[0]
    null_fec = con.execute("SELECT COUNT(*) FROM dw.Fact_Aduana_Item WHERE fecha_key         IS NULL").fetchone()[0]

    print(f"FACT OK: {total:,} filas")
    print(f"  pais_origen_key  NULL: {null_po:,}")
    print(f"  pais_destino_key NULL: {null_pd:,}")
    print(f"  aduana_key       NULL: {null_adu:,}")
    print(f"  fecha_key        NULL: {null_fec:,}")

    if null_po + null_pd + null_adu + null_fec == 0:
        print("\n  [OK] Todos los joins resueltos. Sin nulos en claves foráneas.")
    else:
        print("\n  [ATENCIÓN] Quedan nulos. Ejecutar diagnostico-paises.py para detalle.")

finally:
    con.close()
