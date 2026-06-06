import duckdb
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

# ============================================================================
# CONFIGURACIÓN INICIAL
# ============================================================================
DB_PATH = r"C:/curso-bi/db/aduana.duckdb"
con = duckdb.connect(DB_PATH, read_only=True)

OUTPUT_DIR = r"C:/curso-bi/data_lake/reportes_graficos"
os.makedirs(OUTPUT_DIR, exist_ok=True)

sns.set_theme(style="whitegrid")
plt.rcParams['figure.facecolor'] = 'white'

print("="*80)
print("   GENERACIÓN DE REPORTES GRÁFICOS — AJUSTE DE TIPOS DE GRÁFICOS")
print("="*80)
print("\n[INFO] Fuentes: tablas agregadas (analytic.*) y vistas analíticas\n")

# ============================================================================
# EXTRACCIÓN DE DATOS (MANTENIENDO TU LÓGICA SQL)
# ============================================================================
print("[SQL] Cargando datos desde el Data Warehouse...")
query_r1 = """
    SELECT tipo_operacion, anio, SUM(fob_total) AS fob_anual, SUM(cantidad_items) AS items_totales, ROUND(AVG(fob_promedio), 2) AS ticket_promedio
    FROM analytic.agg_fob_mensual_operacion GROUP BY tipo_operacion, anio ORDER BY tipo_operacion, anio
"""
df_r1 = con.execute(query_r1).fetchdf()

query_r2 = """
    WITH anio_max AS (SELECT MAX(anio) AS anio FROM analytic.agg_fob_pais_anual)
    SELECT a.pais_origen_desc AS pais, SUM(a.fob_total) AS fob_total, SUM(a.cantidad_items) AS items, ROUND(SUM(a.pct_fob_sobre_total), 2) AS pct_del_total
    FROM analytic.agg_fob_pais_anual a JOIN anio_max m ON a.anio = m.anio
    GROUP BY a.pais_origen_desc ORDER BY fob_total DESC LIMIT 10
"""
df_r2 = con.execute(query_r2).fetchdf()

query_r3 = """
    WITH anio_max AS (SELECT MAX(anio) AS anio FROM analytic.v_tendencia_mensual)
    SELECT a.mes_numero, a.mes_nombre, a.tipo_operacion, a.fob_total, a.fob_variacion_pct AS mom_pct, a.fob_ytd
    FROM analytic.v_tendencia_mensual a JOIN anio_max m ON a.anio = m.anio ORDER BY a.tipo_operacion, a.mes_numero
"""
df_r3 = con.execute(query_r3).fetchdf()

query_r4 = """
    WITH anio_max AS (SELECT MAX(anio) AS anio FROM analytic.agg_fob_aduana_mensual)
    SELECT a.nombre_aduana AS aduana, a.tipo_operacion, SUM(a.fob_total) AS fob_anual, SUM(a.cantidad_items) AS items_totales, ROUND(AVG(a.fob_promedio), 2) AS ticket_promedio, ROUND(SUM(a.pct_fob), 2) AS pct_participacion
    FROM analytic.agg_fob_aduana_mensual a JOIN anio_max m ON a.anio = m.anio GROUP BY a.nombre_aduana, a.tipo_operacion ORDER BY a.tipo_operacion, fob_anual DESC
"""
df_r4 = con.execute(query_r4).fetchdf()

query_r5 = """
    WITH anio_max AS (SELECT MAX(anio) AS anio FROM analytic.agg_fob_ncm_anual)
    SELECT a.posicion, LEFT(a.descripcion_arancelaria, 50) AS descripcion, a.rubro, a.tipo_operacion, a.fob_total, a.cantidad_items, a.pct_fob, a.rank_fob
    FROM analytic.agg_fob_ncm_anual a JOIN anio_max m ON a.anio = m.anio WHERE a.rank_fob <= 10 ORDER BY a.tipo_operacion, a.rank_fob
"""
df_r5 = con.execute(query_r5).fetchdf()

query_r6 = """
    WITH anio_max AS (SELECT MAX(anio) AS anio FROM analytic.agg_canal_mensual)
    SELECT a.canal_codigo, a.canal_nombre, a.tipo_operacion, SUM(a.cantidad_despachos) AS total_despachos, ROUND(SUM(a.fob_total) / 1e6, 2) AS fob_millones
    FROM analytic.agg_canal_mensual a JOIN anio_max m ON a.anio = m.anio GROUP BY a.canal_codigo, a.canal_nombre, a.tipo_operacion ORDER BY a.tipo_operacion, total_despachos DESC
"""
df_r6 = con.execute(query_r6).fetchdf()

con.close()

# ============================================================================
# GENERACIÓN DE GRÁFICOS REESTRUCTURADOS
# ============================================================================
print("\n" + "="*80)
print("   EXPORTANDO GRÁFICOS CON NUEVOS FORMATOS SOLICITADOS")
print("="*80 + "\n")

# --- R1: FOB por Operación (Gráfico Circular / Dona)
print("[Exportando] 1_fob_por_operacion.png (CIRCULAR)...")
plt.figure(figsize=(8, 8))
colors_r1 = ['#3498db', '#e67e22']
plt.pie(df_r1['fob_anual'], labels=df_r1['tipo_operacion'], autopct='%1.1f%%', 
        startangle=140, colors=colors_r1, textprops={'fontweight': 'bold', 'fontsize': 12},
        wedgeprops=dict(width=0.4, edgecolor='w', linewidth=2))
plt.title("Distribución Global FOB: Importación vs Exportación (2025)", fontsize=14, fontweight='bold', pad=20)
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "1_fob_por_operacion.png"), dpi=300)
plt.close()

# --- R2: Top 10 Países (Gráfico de Barras / Columnas)
print("[Exportando] 2_top_10_paises.png (BARRAS)...")
plt.figure(figsize=(12, 6))
sns.barplot(data=df_r2, x='pais', y='fob_total', hue='pais', palette='Blues_r', legend=False)
plt.title("Top 10 Países Socios Comerciales — Volumen FOB Anual", fontsize=14, fontweight='bold', pad=20)
plt.xlabel("País de Origen", fontsize=12)
plt.ylabel("FOB Total (USD)", fontsize=12)
plt.ticklabel_format(style='plain', axis='y')
plt.xticks(rotation=35, ha='right')
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "2_top_10_paises.png"), dpi=300)
plt.close()

# --- R3: Tendencia Mensual FOB (Gráfico de Áreas)
print("[Exportando] 3_tendencia_mensual.png (ÁREAS)...")
plt.figure(figsize=(14, 6))
df_r3_pivot = df_r3.pivot_table(index=['mes_numero', 'mes_nombre'], columns='tipo_operacion', values='fob_total').reset_index()
df_r3_pivot = df_r3_pivot.sort_values(by='mes_numero')

plt.fill_between(df_r3_pivot['mes_numero'], df_r3_pivot['IMPORTACION'], label='IMPORTACION', color='#2980b9', alpha=0.4)
plt.plot(df_r3_pivot['mes_numero'], df_r3_pivot['IMPORTACION'], color='#2980b9', linewidth=2)
plt.fill_between(df_r3_pivot['mes_numero'], df_r3_pivot['EXPORTACION'], label='EXPORTACION', color='#27ae60', alpha=0.4)
plt.plot(df_r3_pivot['mes_numero'], df_r3_pivot['EXPORTACION'], color='#27ae60', linewidth=2)

plt.title("Evolución Comercial y Tendencia Mensual FOB (2025)", fontsize=14, fontweight='bold', pad=20)
plt.xlabel("Mes del Año", fontsize=12)
plt.ylabel("Monto FOB Mensual (USD)", fontsize=12)
plt.xticks(df_r3_pivot['mes_numero'], df_r3_pivot['mes_nombre'], rotation=15)
plt.ticklabel_format(style='plain', axis='y')
plt.legend(loc='upper right', title="Operación")
plt.grid(True, alpha=0.2)
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "3_tendencia_mensual.png"), dpi=300)
plt.close()

# --- R4: Ranking de Aduanas (COLUMNA APILADA / STACKED)
print("[Exportando] 4_ranking_aduanas.png (COLUMNA APILADA)...")
fig, ax = plt.subplots(figsize=(14, 7))
# Filtramos las 15 aduanas principales para evitar saturación visual
top_15_aduanas = df_r4.groupby('aduana')['fob_anual'].sum().nlargest(15).index
df_r4_top = df_r4[df_r4['aduana'].isin(top_15_aduanas)]

df_r4_pivot = df_r4_top.pivot_table(index='aduana', columns='tipo_operacion', values='fob_anual', aggfunc='sum').fillna(0)
df_r4_pivot = df_r4_pivot.loc[df_r4_pivot.sum(axis=1).sort_values(ascending=False).index] # Ordenar descendente

df_r4_pivot.plot(kind='bar', stacked=True, ax=ax, width=0.6, color=['#e67e22', '#3498db'], edgecolor='#34495e', linewidth=0.8)
plt.title("Ranking de Principales Aduanas — Volumen FOB Apilado por Operación", fontsize=14, fontweight='bold', pad=20)
plt.xlabel("Administración Aduanera", fontsize=12)
plt.ylabel("FOB Total Administrado (USD)", fontsize=12)
plt.ticklabel_format(style='plain', axis='y')
plt.xticks(rotation=45, ha='right')
plt.legend(title="Tipo Operación")
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "4_ranking_aduanas.png"), dpi=300)
plt.close()

# --- R5: Top 10 NCM (MATRIZ / HEATMAP)
print("[Exportando] 5_top_10_ncm.png (MATRIZ)...")
plt.figure(figsize=(12, 8))
# Agrupamos las posiciones líderes quitando duplicados por trimestre para armar la matriz limpia
df_r5_matrix = df_r5.pivot_table(index='posicion', columns='tipo_operacion', values='fob_total', aggfunc='sum').fillna(0)
df_r5_matrix = df_r5_matrix.sort_values(by=['IMPORTACION', 'EXPORTACION'], ascending=False)

sns.heatmap(df_r5_matrix, annot=True, fmt=",.0f", cmap="Purples", linewidths=1.5, cbar_kws={'label': 'Valor FOB Total (USD)'})
plt.title("Matriz de Posiciones Arancelarias NCM Líderes por Operación", fontsize=14, fontweight='bold', pad=20)
plt.ylabel("Código de Posición Arancelaria NCM", fontsize=12)
plt.xlabel("Flujo Comercial", fontsize=12)
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "5_top_10_ncm.png"), dpi=300)
plt.close()

# --- R6: Canal de Control (COLUMNAS AGRUPADAS / GROUPED)
print("[Exportando] 6_canal_control.png (COLUMNAS AGRUPADAS)...")
fig, ax = plt.subplots(figsize=(12, 6))
df_r6_pivot = df_r6.pivot_table(values='total_despachos', index='tipo_operacion', columns='canal_nombre', aggfunc='sum')

# Aseguramos el orden secuencial del semáforo aduanero
columnas_ordenadas = [col for col in ['VERDE', 'NARANJA', 'ROJO'] if col in df_r6_pivot.columns]
df_r6_pivot = df_r6_pivot[columnas_ordenadas]

# Paleta de colores explícita de la DNIT
paleta_colores = {'VERDE': '#2ecc71', 'NARANJA': '#f39c12', 'ROJO': '#e74c3c'}
colores_actuales = [paleta_colores[col] for col in columnas_ordenadas]

# stacked=False genera columnas una al lado de la otra (Agrupadas)
df_r6_pivot.plot(kind='bar', stacked=False, ax=ax, width=0.6, color=colores_actuales, edgecolor='#2c3e50', linewidth=0.8)
plt.title("Distribución de Canales de Control — Columnas Agrupadas por Operación", fontsize=14, fontweight='bold', pad=20)
plt.xlabel("Flujo Comercial", fontsize=12)
plt.ylabel("Cantidad Absoluta de Despachos", fontsize=12)
plt.ticklabel_format(style='plain', axis='y')
plt.xticks(rotation=0)
plt.legend(title="Canal")
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "6_canal_control.png"), dpi=300)
plt.close()

print("="*80)
print("   [ÉXITO] TODOS LOS REPORTES FUERON RECONFIGURADOS EXITOSAMENTE")
print("="*80)
print(f"Ubicación de imágenes: {OUTPUT_DIR}\n")