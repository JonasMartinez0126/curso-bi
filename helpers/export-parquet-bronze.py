import os
from datetime import datetime
import duckdb

# Carpeta donde están todos los CSV
LANDING_ZONE_CSV = r"C:/curso-bi/data_lake/landing/*.csv"

# Archivo parquet consolidado
BRONZE_SNAPSHOT_PARQUET = r"C:/curso-bi/data_lake/bronze/aduana_item_raw.parquet"


def construir_capa_bronze_parquet():

    print(f"[{datetime.now()}] Iniciando Ingesta Cruda...")

    # Verificar que exista la carpeta landing
    landing_folder = os.path.dirname(
        LANDING_ZONE_CSV.replace("*.csv", "dummy.csv")
    )

    if not os.path.exists(landing_folder):
        raise FileNotFoundError(
            f"No existe la carpeta: {landing_folder}"
        )

    # Crear carpeta destino si no existe
    os.makedirs(
        os.path.dirname(BRONZE_SNAPSHOT_PARQUET),
        exist_ok=True
    )

    con = duckdb.connect(database=':memory:')

    try:

        # Eliminar parquet anterior
        if os.path.exists(BRONZE_SNAPSHOT_PARQUET):
            os.remove(BRONZE_SNAPSHOT_PARQUET)

            print(
                f"[{datetime.now()}] Snapshot anterior eliminado."
            )

        print(
            f"[{datetime.now()}] Leyendo todos los CSV y consolidando..."
        )

        sql_conversion = f"""
        COPY (

            SELECT *

            FROM read_csv_auto(
                '{LANDING_ZONE_CSV}',
                header = true
            )

        )
        TO '{BRONZE_SNAPSHOT_PARQUET}'
        (
            FORMAT PARQUET,
            COMPRESSION ZSTD
        );
        """

        con.execute(sql_conversion)

        total_filas = con.execute(f"""
            SELECT COUNT(*)
            FROM read_parquet('{BRONZE_SNAPSHOT_PARQUET}')
        """).fetchone()[0]

        print(
            f"[{datetime.now()}] ÉXITO: Bronze generado correctamente."
        )

        print(f"Parquet: {BRONZE_SNAPSHOT_PARQUET}")
        print(f"Total registros: {total_filas:,}")

    except Exception as e:

        print(f"ERROR: {str(e)}")
        raise

    finally:
        con.close()


if __name__ == "__main__":
    construir_capa_bronze_parquet()