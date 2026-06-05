"""
================================================================================
CREAR-TABLAS.PY
================================================================================
Script: Inicialización de la Estructura del Data Warehouse (DW)

PROPÓSITO:
  Crear la estructura de base de datos (schema y tablas) necesaria para
  el Data Warehouse de importaciones/exportaciones aduanales.

FLUJO:
  1. Conectarse a la base de datos DuckDB
  2. Crear schema 'dw' (Data Warehouse)
  3. Limpiar tablas existentes (DROP TABLE) para permitir ejecuciones limpias
  4. Crear tabla de staging (stg_aduana) para datos crudos
  5. Crear 6 tablas de dimensión (Dim_*) 
  6. Crear tabla de hechos (Fact_Aduana_Item) con referencias a dimensiones

TABLAS CREADAS:
  
  STAGING (ingesta):
    - dw.stg_aduana: Tabla temporal que recibe datos crudos del parquet
  
  DIMENSIONES (características):
    - dw.Dim_Fecha: Calendario con año, mes, trimestre, semestre
    - dw.Dim_Producto: Posiciones arancelarias NCM, rubros, capítulos
    - dw.Dim_Aduana: Puntos aduaneros, ubicaciones
    - dw.Dim_Pais_Origen: Países de origen de mercancías
    - dw.Dim_Pais_Destino: Países destino de mercancías
    - dw.Dim_Operacion: Tipo de operación (IMPORTACIÓN, EXPORTACIÓN)
    - dw.Dim_Regimen: Regímenes aduanales (admisión, venta, etc)
  
  HECHOS (métricas):
    - dw.Fact_Aduana_Item: Tabla central con FOB, fletes, gravámenes, pesos
      Tiene claves foráneas a todas las dimensiones (modelo estrella)

MODELO:
  Implementa esquema STAR (estrella):
    - Fact_Aduana_Item en el centro
    - Dimensiones conectadas mediante claves foráneas
    - Cada item de despacho se relaciona con 8 dimensiones

AUDITORÍA:
  - batch_id: Identificador único de lote de carga
  - fecha_carga: Timestamp de cuándo se cargó el registro

EJECUCIÓN:
  python sql/crear-tablas.py
  
RESULTADO:
  "Estructura del Data Warehouse creada exitosamente!"
================================================================================
"""

import duckdb

# Ruta a la base de datos DuckDB (archivo local)
DB_PATH = r"C:/curso-bi/db/aduana.duckdb"
con = duckdb.connect(DB_PATH)

sql = """
-- ============================================================================
-- PREPARACIÓN DEL ENTORNO
-- ============================================================================
-- Crear esquema 'dw' si no existe (contenedor lógico de tablas)
CREATE SCHEMA IF NOT EXISTS dw;

-- Limpieza de tablas existentes para permitir ejecuciones idempotentes
-- (se pueden ejecutar múltiples veces sin errores)
DROP TABLE IF EXISTS dw.Fact_Aduana_Item;
DROP TABLE IF EXISTS dw.Dim_Regimen;
DROP TABLE IF EXISTS dw.Dim_Operacion;
DROP TABLE IF EXISTS dw.Dim_Pais_Destino;
DROP TABLE IF EXISTS dw.Dim_Pais_Origen;
DROP TABLE IF EXISTS dw.Dim_Aduana;
DROP TABLE IF EXISTS dw.Dim_Producto;
DROP TABLE IF EXISTS dw.Dim_Fecha;
DROP TABLE IF EXISTS dw.stg_aduana;

-- ============================================================================
-- TABLA DE STAGING (stg_aduana)
-- ============================================================================
-- Propósito: Almacenamiento temporal de datos crudos del parquet
-- Características:
--   - Recibe todos los campos del archivo fuente sin transformación
--   - Campos de auditoría para trazar el origen y momento de carga
--   - Se limpia antes de cada ejecución del ETL
-- ============================================================================
CREATE TABLE IF NOT EXISTS dw.stg_aduana (
    despacho_cifrado VARCHAR,                    -- Identificador del despacho
    operacion VARCHAR,                            -- Tipo: IMPORTACIÓN, EXPORTACIÓN
    destinacion VARCHAR,                          -- Régimen de destinación
    regimen VARCHAR,                              -- Código de régimen aduanal
    oficializacion DATE,                          -- Fecha de oficialización
    cancelacion VARCHAR,                          -- Estado de cancelación
    anio INTEGER,                                 -- Año del despacho
    mes VARCHAR,                                  -- Mes (nombre o número)
    aduana VARCHAR,                               -- Punto aduanero
    cotizacion DECIMAL(18,2),                     -- TC oficial del día
    medio_transporte VARCHAR,                     -- Barco, avión, camión, etc
    canal VARCHAR,                                -- Canal de control: V/R/N
    item INTEGER,                                 -- Número de ítem en despacho
    pais_origen VARCHAR,                          -- País origen de mercancía
    pais_procedencia_destino VARCHAR,             -- País procedencia/destino
    uso VARCHAR,                                  -- Consumo, almacenamiento, etc
    unidad_medida_estadistica VARCHAR,            -- Unidad de medida
    cantidad_estadistica DECIMAL(18,2),           -- Cantidad estadística
    kilo_neto DECIMAL(18,2),                      -- Peso neto en kg
    kilo_bruto DECIMAL(18,2),                     -- Peso bruto en kg
    fob_dolar DECIMAL(18,2),                      -- Valor FOB en USD
    flete_dolar DECIMAL(18,2),                    -- Costo de flete
    seguro_dolar DECIMAL(18,2),                   -- Costo de seguro
    imponible_dolar DECIMAL(18,2),                -- Base imponible en USD
    imponible_gs DECIMAL(18,2),                   -- Base imponible en GS
    ajuste_a_incluir DECIMAL(18,2),               -- Ajustes positivos
    ajuste_a_deducir DECIMAL(18,2),               -- Ajustes negativos
    posicion VARCHAR,                             -- Posición NCM (8 dígitos)
    rubro VARCHAR,                                -- Rubro arancelario
    desc_capitulo VARCHAR,                        -- Descripción capítulo NCM
    desc_partida VARCHAR,                         -- Descripción partida NCM
    desc_posicion VARCHAR,                        -- Descripción posición NCM
    mercaderia VARCHAR,                           -- Descripción mercancía
    marca_item VARCHAR,                           -- Marca del producto
    acuerdo VARCHAR,                              -- Acuerdo comercial aplicable
    numero_subitem INTEGER,                       -- Número de subitem
    cantidad_subitem DECIMAL(18,2),               -- Cantidad de subitems
    precio_unitario_subitem DECIMAL(18,2),        -- Precio por subitem
    desc_subitem VARCHAR,                         -- Descripción subitem
    marca_subitem VARCHAR,                        -- Marca subitem
    derecho DECIMAL(18,2),                        -- Arancel (derecho aduanal)
    isc DECIMAL(18,2),                            -- Impuesto Selectivo al Consumo
    servicio DECIMAL(18,2),                       -- Tasa de servicio aduanal
    renta DECIMAL(18,2),                          -- Impuesto a la Renta
    iva DECIMAL(18,2),                            -- Impuesto al Valor Agregado
    otros DECIMAL(18,2),                          -- Otros gravámenes
    total DECIMAL(18,2),                          -- Total de gravámenes
    -- Campos de auditoría
    batch_id VARCHAR,                             -- Identificador de lote de carga
    fecha_carga TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Cuándo se cargó
    archivo_origen VARCHAR                        -- De qué archivo proviene
);

-- ============================================================================
-- DIMENSIÓN: FECHA (dw.Dim_Fecha)
-- ============================================================================
-- Propósito: Calendario para contexto temporal
-- Características:
--   - fecha_key: Clave numérica para joins (YYYYMMDD)
--   - Facilita análisis por mes, trimestre, semestre
--   - Permite comparaciones year-to-year (YoY)
-- Grano: 1 fila por día
-- ============================================================================
CREATE TABLE dw.Dim_Fecha (
    fecha_key INTEGER PRIMARY KEY,                  -- Clave: YYYYMMDD (formato numérico)
    fecha_oficializacion DATE NOT NULL,             -- Fecha real del calendario
    anio INTEGER NOT NULL,                          -- Año (2025, 2026, etc)
    mes_nombre VARCHAR(20),                         -- "Enero", "Febrero", etc
    mes_numero INTEGER,                             -- 1-12
    trimestre INTEGER,                              -- 1-4
    semestre INTEGER                                -- 1-2
);

-- ============================================================================
-- DIMENSIÓN: PRODUCTO (dw.Dim_Producto)
-- ============================================================================
-- Propósito: Catálogo de posiciones arancelarias NCM
-- Características:
--   - Agrupa mercancías por jerarquía (rubro -> capítulo -> partida -> posición)
--   - Posición es el nivel más detallado (8 dígitos)
--   - Facilita análisis por categoría de producto
-- Grano: 1 fila por posición NCM única
-- ============================================================================
CREATE TABLE dw.Dim_Producto (
    producto_key INTEGER PRIMARY KEY,               -- Clave numérica
    rubro VARCHAR,                                  -- Rubro general ("ALIMENTOS", etc)
    capitulo VARCHAR(100),                          -- Capítulo NCM (2 dígitos)
    partida VARCHAR(100),                           -- Partida NCM (4 dígitos)
    posicion VARCHAR(20),                           -- Posición NCM (8 dígitos - más específica)
    descripcion_arancelaria VARCHAR(500)            -- Descripción completa de la posición
);

-- ============================================================================
-- DIMENSIÓN: ADUANA (dw.Dim_Aduana)
-- ============================================================================
-- Propósito: Catálogo de puntos aduaneros
-- Características:
--   - Cada punto aduanero es un puerto, aeropuerto o paso terrestre
--   - nombre_aduana: ej "PUERTO DE ASUNCIÓN", "AEROPUERTO SILVIO PETTIROSSI"
--   - ubicacion_dependencia: Localización geográfica
-- Grano: 1 fila por punto aduanero
-- ============================================================================
CREATE TABLE dw.Dim_Aduana (
    aduana_key INTEGER PRIMARY KEY,                 -- Clave numérica
    nombre_aduana VARCHAR(100),                     -- Nombre del punto aduanero
    ubicacion_dependencia VARCHAR(100)              -- Ubicación geográfica
);

-- ============================================================================
-- DIMENSIÓN: PAÍS ORIGEN (dw.Dim_Pais_Origen)
-- ============================================================================
-- Propósito: Catálogo de países de origen de mercancías
-- Características:
--   - Usado en importaciones (de dónde viene la mercancía)
--   - Permite análisis de flujos comerciales por país
-- Grano: 1 fila por país único
-- ============================================================================
CREATE TABLE dw.Dim_Pais_Origen (
    pais_origen_key INTEGER PRIMARY KEY,            -- Clave numérica
    pais_origen_desc VARCHAR(100)                   -- Nombre del país
);

-- ============================================================================
-- DIMENSIÓN: PAÍS DESTINO (dw.Dim_Pais_Destino)
-- ============================================================================
-- Propósito: Catálogo de países destino de mercancías
-- Características:
--   - Usado en exportaciones (hacia dónde va la mercancía)
--   - También puede usarse en re-exportaciones
-- Grano: 1 fila por país único
-- ============================================================================
CREATE TABLE dw.Dim_Pais_Destino (
    pais_destino_key INTEGER PRIMARY KEY,           -- Clave numérica
    pais_desc_desc VARCHAR(100)                     -- Nombre del país destino
);

-- ============================================================================
-- DIMENSIÓN: OPERACIÓN (dw.Dim_Operacion)
-- ============================================================================
-- Propósito: Tipo de operación aduanal
-- Características:
--   - Valores típicos: IMPORTACIÓN, EXPORTACIÓN
--   - Permite segmentar análisis entre entrada y salida de mercancías
-- Grano: 1 fila por tipo de operación (muy pequeña ~2 filas)
-- ============================================================================
CREATE TABLE dw.Dim_Operacion (
    operacion_key INTEGER PRIMARY KEY,              -- Clave numérica
    tipo_operacion VARCHAR(20)                      -- "IMPORTACIÓN" o "EXPORTACIÓN"
);

-- ============================================================================
-- DIMENSIÓN: RÉGIMEN (dw.Dim_Regimen)
-- ============================================================================
-- Propósito: Regímenes aduanales aplicables
-- Características:
--   - Régimen: Marco legal para tratar la mercancía
--   - Valores: Admisión, Venta, Compraventa, etc
--   - Define derechos y obligaciones aduanales
-- Grano: 1 fila por régimen aduanal
-- ============================================================================
CREATE TABLE dw.Dim_Regimen (
    regimen_key INTEGER PRIMARY KEY,                -- Clave numérica
    codigo_regimen VARCHAR(10),                     -- Código del régimen
    descripcion_regimen VARCHAR(200)                -- Descripción del régimen
);

-- ============================================================================
-- TABLA DE HECHOS: FACT_ADUANA_ITEM (dw.Fact_Aduana_Item)
-- ============================================================================
-- Propósito: Tabla central del modelo estrella
-- Almacena: HECHOS (eventos de despachos aduanales)
--
-- CARACTERÍSTICAS:
--   - 1 fila = 1 ítem de 1 despacho aduanal
--   - Contiene todas las métricas (FOB, fletes, gravámenes, etc)
--   - Las claves foráneas conectan con las 7 dimensiones
--   - Diseño optimizado para análisis rápidos
--
-- MÉTRICAS PRINCIPALES:
--   - fob_dolar: Valor Free On Board (base del arancel)
--   - flete_dolar: Costo de transporte
--   - seguro_dolar: Costo de seguro
--   - derecho, isc, iva: Gravámenes específicos
--   - total_gravamen: Suma de todos los gravámenes
--   - kilo_neto / kilo_bruto: Pesos
--
-- AUDITORÍA:
--   - canal: Canal de control (V=VERDE riesgo bajo, R=ROJO riesgo alto)
--   - batch_id: Identificador de lote de ETL
--   - fecha_carga: Cuándo fue procesado
--
-- GRANO: 1 fila por ítem de despacho (millones de filas esperadas)
-- ============================================================================
CREATE TABLE dw.Fact_Aduana_Item (
    id_fact_key BIGINT PRIMARY KEY,                 -- Clave única de la fila
    fecha_key INTEGER REFERENCES dw.Dim_Fecha(fecha_key),
    aduana_key INTEGER REFERENCES dw.Dim_Aduana(aduana_key),
    producto_key INTEGER REFERENCES dw.Dim_Producto(producto_key),
    pais_origen_key INTEGER REFERENCES dw.Dim_Pais_Origen(pais_origen_key),
    pais_destino_key INTEGER REFERENCES dw.Dim_Pais_Destino(pais_destino_key),
    operacion_key INTEGER REFERENCES dw.Dim_Operacion(operacion_key),
    regimen_key INTEGER REFERENCES dw.Dim_Regimen(regimen_key),
    
    -- ========== MÉTRICAS DEL ÍTEM ==========
    -- Cantidades en peso (kilogramos)
    kilo_neto DECIMAL(18,2),                        -- Peso neto en kg
    kilo_bruto DECIMAL(18,2),                       -- Peso bruto en kg
    
    -- Valores monetarios (USD)
    fob_dolar DECIMAL(18,2),                        -- Valor FOB (Free On Board)
    flete_dolar DECIMAL(18,2),                      -- Costo del flete
    seguro_dolar DECIMAL(18,2),                     -- Costo del seguro
    
    -- Gravámenes (USD)
    derecho DECIMAL(18,2),                          -- Derecho aduanal
    isc DECIMAL(18,2),                              -- Impuesto Selectivo al Consumo
    iva DECIMAL(18,2),                              -- Impuesto al Valor Agregado
    total_gravamen DECIMAL(18,2),                   -- Suma de gravámenes
    
    -- ========== MÉTRICAS DE SUBITEM ==========
    -- Desagregación adicional de información del ítem
    valor_fob_subitem DECIMAL(18,2),                -- FOB a nivel de subitem
    kilo_neto_subitem DECIMAL(18,2),                -- Peso neto subitem
    
    -- ========== AUDITORÍA ==========
    canal VARCHAR(20),                              -- Canal de control (V/R/N)
    batch_id VARCHAR(20),                           -- ID del lote ETL
    fecha_carga TIMESTAMP DEFAULT CURRENT_TIMESTAMP -- Cuándo se procesó
);
"""

# Ejecutar el script SQL
con.execute(sql)
con.close()

print("Estructura del Data Warehouse creada exitosamente!")