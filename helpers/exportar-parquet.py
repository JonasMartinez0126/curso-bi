import duckdb
import os

DB_PATH = r"C:\curso-bi\db\aduana.duckdb"
EXPORT_DIR = r"C:\curso-bi\data_lake\powerbi"

TABLAS = [
    "dw.Fact_Aduana_Item",
    "dw.Dim_Fecha",
    "dw.Dim_Aduana",
    "dw.Dim_Producto",
    "dw.Dim_Pais_Origen",
    "dw.Dim_Pais_Destino",
    "dw.Dim_Operacion",
    "dw.Dim_Regimen",
]

# read_only=True es una excelente práctica para exportar
con = duckdb.connect(DB_PATH, read_only=True)
os.makedirs(EXPORT_DIR, exist_ok=True)

print("=== EXPORTANDO TABLAS DEL DW A PARQUET PARA POWER BI ===\n")

for tabla in TABLAS:
    nombre_archivo = tabla.replace("dw.", "") + ".parquet"
    ruta_salida = os.path.join(EXPORT_DIR, nombre_archivo)
    
    # CORRECCIÓN CLAVE: DuckDB requiere barras diagonales (/) dentro de los strings SQL.
    # Reemplazamos las barras invertidas de Windows para evitar errores de escape.
    ruta_salida_sql = ruta_salida.replace("\\", "/")

    try:
        filas = con.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
        
        # Usamos la ruta formateada 'ruta_salida_sql'
        con.execute(f"""
            COPY (SELECT * FROM {tabla})
            TO '{ruta_salida_sql}'
            (FORMAT 'PARQUET', COMPRESSION 'ZSTD');
        """)
        print(f"  OK  {tabla:35} -> {nombre_archivo}  ({filas:,} filas)")
    except Exception as e:
        print(f"  ERR {tabla}: {e}")

con.close()
print(f"\nArchivos guardados exitosamente en: {EXPORT_DIR}")
print("=== EXPORTACION COMPLETADA ===")