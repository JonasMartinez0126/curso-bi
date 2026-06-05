import duckdb
import os

DB_PATH = r"C:\curso-bi\db\aduana.duckdb"

# ------------------------------------------------------------------
# ARQUITECTURA DE CAPAS DEL DATA LAKE
#
# BRONZE  -> datos crudos del parquet original
# SILVER  -> dimensiones: datos limpios, normalizados y con surrogate keys
# GOLD    -> tabla de hechos: modelo estrella listo para consumo analítico
# powerbi -> carpeta de conveniencia que apunta a silver + gold para PBI
# ------------------------------------------------------------------

CAPA_SILVER = r"C:\curso-bi\data_lake\silver"
CAPA_GOLD   = r"C:\curso-bi\data_lake\gold"

# Dimensiones -> Silver (datos limpios y estandarizados, reutilizables)
TABLAS_SILVER = [
    "dw.Dim_Fecha",
    "dw.Dim_Aduana",
    "dw.Dim_Producto",
    "dw.Dim_Pais_Origen",
    "dw.Dim_Pais_Destino",
    "dw.Dim_Operacion",
    "dw.Dim_Regimen",
]

# Tabla de hechos -> Gold (modelo estrella, listo para BI y analítica)
TABLAS_GOLD = [
    "dw.Fact_Aduana_Item",
]

def exportar_capa(con, tablas, directorio, nombre_capa):
    os.makedirs(directorio, exist_ok=True)
    print(f"\n  [{nombre_capa}]  destino: {directorio}")
    print(f"  {'─' * 60}")

    errores = []
    for tabla in tablas:
        nombre_archivo = tabla.replace("dw.", "") + ".parquet"
        ruta_salida    = os.path.join(directorio, nombre_archivo)
        # DuckDB requiere barras forward dentro del SQL
        ruta_sql       = ruta_salida.replace("\\", "/")

        try:
            filas = con.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
            con.execute(f"""
                COPY (SELECT * FROM {tabla})
                TO '{ruta_sql}'
                (FORMAT 'PARQUET', COMPRESSION 'ZSTD')
            """)
            print(f"  OK  {tabla:35} -> {nombre_archivo:35} ({filas:>10,} filas)")
        except Exception as e:
            print(f"  ERR {tabla}: {e}")
            errores.append(tabla)

    return errores


# ------------------------------------------------------------------
# EJECUCIÓN
# ------------------------------------------------------------------
print("=" * 65)
print("   EXPORTANDO DATA WAREHOUSE A PARQUET POR CAPAS")
print("=" * 65)

# read_only=True: protege el DW de escrituras accidentales durante export
con = duckdb.connect(DB_PATH, read_only=True)

errores_total = []

errores_total += exportar_capa(con, TABLAS_SILVER, CAPA_SILVER, "SILVER — Dimensiones")
errores_total += exportar_capa(con, TABLAS_GOLD,   CAPA_GOLD,   "GOLD   — Hechos")

con.close()

# ------------------------------------------------------------------
# RESUMEN FINAL
# ------------------------------------------------------------------
print(f"\n{'─' * 65}")
print(f"  Silver: {CAPA_SILVER}")
print(f"  Gold:   {CAPA_GOLD}")

if errores_total:
    print(f"\n  [ATENCIÓN] {len(errores_total)} tabla(s) no exportada(s): {errores_total}")
else:
    print(f"\n  [OK] Todas las tablas exportadas sin errores.")

print("=" * 65)