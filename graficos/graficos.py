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
print("  GENERACIÓN DE REPORTES GRÁFICOS — ANÁLISIS OLAP")
print("="*80)
print("\n[INFO] Fuentes: tablas agregadas (analytic.*) y vistas analíticas\n")

# ============================================================================
# R1: FOB POR OPERACIÓN CON VARIACIÓN ANUAL
# ============================================================================
print("[SQL] Cargando R1: FOB por Operación con Variación Anual...")
query_r1 = """
    SELECT
        tipo_operacion,
        anio,
        SUM(fob_total) AS fob_anual,
        SUM(cantidad_items) AS items_totales,
        ROUND(AVG(fob_promedio), 2) AS ticket_promedio
    FROM analytic.agg_fob_mensual_operacion
    GROUP BY tipo_operacion, anio
    ORDER BY tipo_operacion, anio
"""
df_r1 = con.execute(query_r1).fetchdf()

# ============================================================================
# R2: TOP 10 PAÍSES ORIGEN (AÑO MÁS RECIENTE)
# ============================================================================
print("[SQL] Cargando R2: Top 10 Países Origen...")
query_r2 = """
    WITH anio_max AS (
        SELECT MAX(anio) AS anio FROM analytic.agg_fob_pais_anual
    )
    SELECT
        a.pais_origen_desc AS pais,
        SUM(a.fob_total) AS fob_total,
        SUM(a.cantidad_items) AS items,
        ROUND(SUM(a.pct_fob_sobre_total), 2) AS pct_del_total
    FROM analytic.agg_fob_pais_anual a
    JOIN anio_max m ON a.anio = m.anio
    GROUP BY a.pais_origen_desc
    ORDER BY fob_total DESC
    LIMIT 10
"""
df_r2 = con.execute(query_r2).fetchdf()

# ============================================================================
# R3: TENDENCIA MENSUAL FOB (AÑO MÁS RECIENTE)
# ============================================================================
print("[SQL] Cargando R3: Tendencia Mensual...")
query_r3 = """
    WITH anio_max AS (
        SELECT MAX(anio) AS anio FROM analytic.v_tendencia_mensual
    )
    SELECT
        a.mes_numero,
        a.mes_nombre,
        a.tipo_operacion,
        a.fob_total,
        a.fob_variacion_pct AS mom_pct,
        a.fob_ytd
    FROM analytic.v_tendencia_mensual a
    JOIN anio_max m ON a.anio = m.anio
    ORDER BY a.tipo_operacion, a.mes_numero
"""
df_r3 = con.execute(query_r3).fetchdf()

# ============================================================================
# R4: RANKING ADUANAS POR FOB (AÑO MÁS RECIENTE)
# ============================================================================
print("[SQL] Cargando R4: Ranking de Aduanas...")
query_r4 = """
    WITH anio_max AS (
        SELECT MAX(anio) AS anio FROM analytic.agg_fob_aduana_mensual
    )
    SELECT
        a.nombre_aduana AS aduana,
        a.tipo_operacion,
        SUM(a.fob_total) AS fob_anual,
        SUM(a.cantidad_items) AS items_totales,
        ROUND(AVG(a.fob_promedio), 2) AS ticket_promedio,
        ROUND(SUM(a.pct_fob), 2) AS pct_participacion
    FROM analytic.agg_fob_aduana_mensual a
    JOIN anio_max m ON a.anio = m.anio
    GROUP BY a.nombre_aduana, a.tipo_operacion
    ORDER BY a.tipo_operacion, fob_anual DESC
"""
df_r4 = con.execute(query_r4).fetchdf()

# ============================================================================
# R5: TOP 10 NCM POR FOB (AÑO MÁS RECIENTE)
# ============================================================================
print("[SQL] Cargando R5: Top 10 NCM...")
query_r5 = """
    WITH anio_max AS (
        SELECT MAX(anio) AS anio FROM analytic.agg_fob_ncm_anual
    )
    SELECT
        a.posicion,
        LEFT(a.descripcion_arancelaria, 50) AS descripcion,
        a.rubro,
        a.tipo_operacion,
        a.fob_total,
        a.cantidad_items,
        a.pct_fob,
        a.rank_fob
    FROM analytic.agg_fob_ncm_anual a
    JOIN anio_max m ON a.anio = m.anio
    WHERE a.rank_fob <= 10
    ORDER BY a.tipo_operacion, a.rank_fob
"""
df_r5 = con.execute(query_r5).fetchdf()

# ============================================================================
# R6: CANAL DE CONTROL (AÑO MÁS RECIENTE)
# ============================================================================
print("[SQL] Cargando R6: Canal de Control...")
query_r6 = """
    WITH anio_max AS (
        SELECT MAX(anio) AS anio FROM analytic.agg_canal_mensual
    )
    SELECT
        a.canal_codigo,
        a.canal_nombre,
        a.tipo_operacion,
        SUM(a.cantidad_despachos) AS total_despachos,
        ROUND(SUM(a.fob_total) / 1e6, 2) AS fob_millones,
        ROUND(
            SUM(a.cantidad_despachos) * 100.0
            / SUM(SUM(a.cantidad_despachos)) OVER (
                PARTITION BY a.tipo_operacion
            ), 2
        ) AS pct_del_total
    FROM analytic.agg_canal_mensual a
    JOIN anio_max m ON a.anio = m.anio
    GROUP BY a.canal_codigo, a.canal_nombre, a.tipo_operacion
    ORDER BY a.tipo_operacion, total_despachos DESC
"""
df_r6 = con.execute(query_r6).fetchdf()

con.close()

# ============================================================================
# GENERACIÓN DE GRÁFICOS
# ============================================================================
print("\n" + "="*80)
print("  EXPORTANDO GRÁFICOS")
print("="*80 + "\n")

# --- R1: FOB por Operación (Gráfico de línea)
print("[Exportando] 1_fob_por_operacion.png...")
plt.figure(figsize=(12, 6))
for operacion in df_r1['tipo_operacion'].unique():
    data = df_r1[df_r1['tipo_operacion'] == operacion]
    plt.plot(data['anio'], data['fob_anual'], marker='o', label=operacion, linewidth=2.5)
plt.title("FOB por Tipo de Operación — Tendencia Anual", fontsize=14, fontweight='bold', pad=20)
plt.xlabel("Año", fontsize=12)
plt.ylabel("FOB Total (USD)", fontsize=12)
plt.legend(loc='best')
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "1_fob_por_operacion.png"), dpi=300, bbox_inches='tight')
plt.close()

# --- R2: Top 10 Países (Gráfico de barras horizontal)
print("[Exportando] 2_top_10_paises.png...")
plt.figure(figsize=(12, 8))
sns.barplot(data=df_r2, x='fob_total', y='pais', orient='h', palette='viridis', hue='pais', legend=False)
plt.title("Top 10 Países Socios Comerciales — Volumen FOB", fontsize=14, fontweight='bold', pad=20)
plt.xlabel("FOB Total (USD)", fontsize=12)
plt.ylabel("País", fontsize=12)
plt.ticklabel_format(style='plain', axis='x')
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "2_top_10_paises.png"), dpi=300, bbox_inches='tight')
plt.close()

# --- R3: Tendencia Mensual (Gráfico de línea con MoM)
print("[Exportando] 3_tendencia_mensual.png...")
plt.figure(figsize=(14, 7))
df_r3_sorted = df_r3.sort_values(by='mes_numero')
for operacion in df_r3_sorted['tipo_operacion'].unique():
    data = df_r3_sorted[df_r3_sorted['tipo_operacion'] == operacion]
    plt.plot(data['mes_numero'], data['fob_total'], marker='o', label=operacion, linewidth=2.5)
plt.title("Tendencia Mensual FOB — Year-to-Date", fontsize=14, fontweight='bold', pad=20)
plt.xlabel("Mes", fontsize=12)
plt.ylabel("FOB Total (USD)", fontsize=12)
plt.xticks(range(1, 13))
plt.legend(loc='best')
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "3_tendencia_mensual.png"), dpi=300, bbox_inches='tight')
plt.close()

# --- R4: Ranking de Aduanas (Gráfico de barras, separado por operación)
print("[Exportando] 4_ranking_aduanas.png...")
fig, axes = plt.subplots(1, 2, figsize=(16, 7))
for idx, operacion in enumerate(df_r4['tipo_operacion'].unique()):
    data = df_r4[df_r4['tipo_operacion'] == operacion].head(8)
    sns.barplot(data=data, x='fob_anual', y='aduana', ax=axes[idx], palette='magma', hue='aduana', legend=False)
    axes[idx].set_title(f"Ranking Aduanas — {operacion}", fontsize=12, fontweight='bold')
    axes[idx].set_xlabel("FOB Total (USD)", fontsize=11)
    axes[idx].set_ylabel("Aduana", fontsize=11)
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "4_ranking_aduanas.png"), dpi=300, bbox_inches='tight')
plt.close()

# --- R5: Top 10 NCM (Gráfico de barras, separado por operación)
print("[Exportando] 5_top_10_ncm.png...")
fig, axes = plt.subplots(1, 2, figsize=(16, 8))
for idx, operacion in enumerate(df_r5['tipo_operacion'].unique()):
    data = df_r5[df_r5['tipo_operacion'] == operacion].head(10)
    axes[idx].barh(range(len(data)), data['fob_total'], color='steelblue')
    axes[idx].set_yticks(range(len(data)))
    axes[idx].set_yticklabels([desc[:30] + "..." if len(desc) > 30 else desc 
                               for desc in data['descripcion']], fontsize=9)
    axes[idx].set_title(f"Top 10 NCM — {operacion}", fontsize=12, fontweight='bold')
    axes[idx].set_xlabel("FOB Total (USD)", fontsize=11)
    axes[idx].invert_yaxis()
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "5_top_10_ncm.png"), dpi=300, bbox_inches='tight')
plt.close()

# --- R6: Canal de Control (Gráfico de barras apiladas)
print("[Exportando] 6_canal_control.png...")
fig, ax = plt.subplots(figsize=(12, 7))
pivot_data = df_r6.pivot_table(values='total_despachos', 
                               index='tipo_operacion', 
                               columns='canal_nombre', 
                               aggfunc='sum')
pivot_data.plot(kind='bar', ax=ax, width=0.7, color=['#2ecc71', '#e74c3c', '#f39c12'])
plt.title("Distribución de Canales de Control — Por Tipo de Operación", fontsize=14, fontweight='bold', pad=20)
plt.xlabel("Tipo de Operación", fontsize=12)
plt.ylabel("Cantidad de Despachos", fontsize=12)
plt.xticks(rotation=0)
plt.legend(title="Canal", bbox_to_anchor=(1.05, 1), loc='upper left')
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "6_canal_control.png"), dpi=300, bbox_inches='tight')
plt.close()

# ============================================================================
# RESUMEN FINAL
# ============================================================================
print("\n" + "="*80)
print("  [OK] REPORTES GENERADOS EXITOSAMENTE")
print("="*80)
print(f"\nUbicación: {OUTPUT_DIR}\n")
print("Reportes generados:")
print("  1. fob_por_operacion.png   — Tendencia anual por tipo de operación")
print("  2. top_10_paises.png       — Top 10 países socios comerciales")
print("  3. tendencia_mensual.png   — Evolución mes a mes (YTD)")
print("  4. ranking_aduanas.png     — Ranking de aduanas por operación")
print("  5. top_10_ncm.png          — Top 10 posiciones arancelarias")
print("  6. canal_control.png       — Distribución de canales VERDE/ROJO/NARANJA")
print("\n" + "="*80)