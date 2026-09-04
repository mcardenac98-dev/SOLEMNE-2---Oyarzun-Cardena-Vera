import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt

# ==============================================================================
# CONFIGURACIÓN DE PÁGINA
# ==============================================================================
st.set_page_config(
    page_title="Dashboard REM20 - Salud Chile",
    page_icon="🏥",
    layout="wide"
)

# ==============================================================================
# DICCIONARIO TERRITORIAL EXHAUSTIVO
# Mapea Servicios de Salud (GLOSA_SSS) con sus regiones político-administrativas
# ==============================================================================
MAPA_REGIONES = {
    "Región de Arica y Parinacota": ["Arica"],
    "Región de Tarapacá": ["Tarapacá", "Tarapaca"],
    "Región de Antofagasta": ["Antofagasta"],
    "Región de Atacama": ["Atacama"],
    "Región de Coquimbo": ["Coquimbo"],
    "Región de Valparaíso": ["Valparaíso", "Valparaiso", "Viña del Mar", "Aconcagua"],
    "Región Metropolitana": [
        "Metropolitano Central", "Metropolitano Norte", "Metropolitano Oriente",
        "Metropolitano Sur", "Metropolitano Sur Oriente", "Metropolitano Occidente"
    ],
    "Región de O'Higgins": [
        "Libertador B. O'Higgins", "Libertador B.O'Higgins", "O'Higgins", "Ohiggins", "Rancagua"
    ],
    "Región del Maule": ["Maule", "Del Maule", "Talca"],
    "Región de Ñuble": ["Ñuble", "Nuble"],
    "Región del Biobío": ["Concepción", "Concepcion", "Talcahuano", "Biobío", "Biobio", "Arauco"],
    "Región de La Araucanía": ["Araucanía Norte", "Araucanía Sur", "Araucania Norte", "Araucania Sur"],
    "Región de Los Ríos": ["Valdivia", "Los Ríos", "Los Rios"],
    "Región de Los Lagos": ["Osorno", "Reloncaví", "Reloncavi", "Chiloé", "Chiloe", "Los Lagos"],
    "Región de Aysén": [
        "Aysén", "Aysen", "Aysén del General Carlos Ibáñez del Campo",
        "Aysen del General Carlos Ibañez del Campo", "Coyhaique"
    ],
    "Región de Magallanes": ["Magallanes", "Punta Arenas"]
}

def asignar_region(glosa):
    if not isinstance(glosa, str):
        return "Otras"
    glosa_limpia = glosa.lower()
    for region, servicios in MAPA_REGIONES.items():
        for srv in servicios:
            if srv.lower() in glosa_limpia:
                return region
    return "Otras"

# ==============================================================================
# CARGA Y PROCESAMIENTO DE DATOS CON CACHÉ
# ==============================================================================
@st.cache_data(show_spinner=True)
def cargar_datos_minsal():
    url = "https://datos.gob.cl/api/3/action/datastore_search?resource_id=657cc933-eac8-4bfc-b004-c4d6dcd988a8&limit=50000"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=20)
        if res.status_code == 200:
            datos = res.json()["result"]["records"]
            df_raw = pd.DataFrame(datos)
            
            # Casteo numérico explícito y tratamiento de nulos
            columnas_num = ["INDICE_OCUPACIONAL", "NUMERO_EGRESOS", "DIAS_ESTADA", "LETALIDAD"]
            for col in columnas_num:
                if col in df_raw.columns:
                    df_raw[col] = pd.to_numeric(df_raw[col], errors="coerce").fillna(0)
                else:
                    df_raw[col] = 0.0
            
            # Asignación de región
            if "GLOSA_SSS" in df_raw.columns:
                df_raw["REGION"] = df_raw["GLOSA_SSS"].apply(asignar_region)
            else:
                df_raw["REGION"] = "Desconocida"
                
            return df_raw
        else:
            return pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()

# Cargar dataset
df = cargar_datos_minsal()

if df.empty:
    st.error("No se pudo conectar a la API de datos.gob.cl o no se recibieron registros.")
    st.stop()

# ==============================================================================
# BARRA LATERAL: FILTROS DINÁMICOS EN CASCADA
# ==============================================================================
st.sidebar.title("🗺️ Filtros Territoriales")

# 1. Filtro Región
regiones_disponibles = list(MAPA_REGIONES.keys())
region_sel = st.sidebar.selectbox("Seleccione Región:", regiones_disponibles, index=6)

df_region = df[df["REGION"] == region_sel]

# 2. Filtro Establecimiento
todos_los_est = st.sidebar.checkbox("Incluir todos los establecimientos", value=True)
if not todos_los_est:
    establecimientos = sorted(df_region["ESTABLECIMIENTO"].dropna().unique())
    est_sel = st.sidebar.multiselect("Seleccione Establecimiento(s):", establecimientos)
    if est_sel:
        df_region = df_region[df_region["ESTABLECIMIENTO"].isin(est_sel)]

# 3. Filtro Especialidad / Área Funcional (Dinámico por Región)
especialidades_disponibles = sorted(df_region["AREA_FUNCIONAL"].dropna().unique().tolist())

# Preselección adaptativa: hasta 5 especialidades válidas del territorio
default_especialidades = especialidades_disponibles[:5] if len(especialidades_disponibles) >= 5 else especialidades_disponibles

especialidades_sel = st.sidebar.multiselect(
    "Especialidad / Área Funcional:",
    options=especialidades_disponibles,
    default=default_especialidades
)

if especialidades_sel:
    df_filtrado = df_region[df_region["AREA_FUNCIONAL"].isin(especialidades_sel)]
else:
    df_filtrado = df_region

# ==============================================================================
# PANEL PRINCIPAL Y KPIS
# ==============================================================================
st.title("🏥 Indicadores Hospitalarios por Región y Establecimiento (REM20)")
st.caption("Monitoreo interactivo de la Red Pública Hospitalaria con datos de **datos.gob.cl** (MINSAL).")

st.markdown(f"### 📌 Resumen: {region_sel}")

col1, col2, col3, col4 = st.columns(4)

total_registros = len(df_filtrado)
ocupacion_media = df_filtrado["INDICE_OCUPACIONAL"].mean() if total_registros > 0 else 0
total_egresos = df_filtrado["NUMERO_EGRESOS"].sum() if total_registros > 0 else 0
letalidad_media = df_filtrado["LETALIDAD"].mean() if total_registros > 0 else 0

col1.metric("Registros", f"{total_registros:,}")
col2.metric("Ocupación Camas", f"{ocupacion_media:.1f}%")
col3.metric("Total Egresos", f"{int(total_egresos):,}")
col4.metric("Letalidad Media", f"{letalidad_media:.1f}%")

st.divider()

# ==============================================================================
# VISUALIZACIÓN GRÁFICA
# ==============================================================================
st.subheader("📊 Visualización Gráfica")

tab1, tab2 = st.tabs(["Ocupación por Establecimiento", "Egresos vs Días de Estada"])

with tab1:
    if not df_filtrado.empty:
        # Filtrar valores clínicos coherentes (excluye recintos ambulatorios sin camas fijas)
        df_ocupacion = df_filtrado[(df_filtrado["INDICE_OCUPACIONAL"] > 0) & (df_filtrado["INDICE_OCUPACIONAL"] <= 100)]
        
        if not df_ocupacion.empty:
            ranking = (
                df_ocupacion.groupby("ESTABLECIMIENTO")["INDICE_OCUPACIONAL"]
                .mean()
                .sort_values(ascending=True)
                .tail(10)
            )
            
            fig, ax = plt.subplots(figsize=(10, 5))
            barras = ax.barh(ranking.index, ranking.values, color="#1f77b4", edgecolor="black", alpha=0.85)
            ax.set_xlim(0, 105)
            ax.set_xlabel("Índice Ocupacional Promedio (%)", fontsize=11)
            ax.set_title("Top 10 Hospitales con Mayor Demanda y Ocupación (%)", fontsize=12, fontweight="bold")
            ax.grid(axis="x", linestyle="--", alpha=0.6)
            
            # Etiquetas de valor porcentual en cada barra
            for bar in barras:
                ancho = bar.get_width()
                ax.text(ancho + 1, bar.get_y() + bar.get_height() / 2, f"{ancho:.1f}%",
                        ha="left", va="center", fontsize=9, color="#222")
            
            plt.tight_layout()
            st.pyplot(fig)
        else:
            st.info("No hay datos de ocupación válidos (1% - 100%) para la combinación seleccionada.")
    else:
        st.info("Sin registros para la selección actual.")

with tab2:
    if not df_filtrado.empty:
        # Tratamiento estadístico de outliers mediante corte por percentil 98
        p98_estada = df_filtrado["DIAS_ESTADA"].quantile(0.98)
        df_dispersion = df_filtrado[df_filtrado["DIAS_ESTADA"] <= (p98_estada if p98_estada > 0 else df_filtrado["DIAS_ESTADA"].max())]
        
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.scatter(df_dispersion["NUMERO_EGRESOS"], df_dispersion["DIAS_ESTADA"], 
                   color="#2ca02c", alpha=0.5, edgecolors="none", s=40)
        ax.set_title("Relación entre Altas Clínicas (Egresos) y Días de Estada Acumulados", fontsize=12, fontweight="bold")
        ax.set_xlabel("Número de Egresos", fontsize=11)
        ax.set_ylabel("Días de Estada", fontsize=11)
        ax.grid(True, linestyle="--", alpha=0.5)
        
        plt.tight_layout()
        st.pyplot(fig)
    else:
        st.info("Sin registros para la selección actual.")

# ==============================================================================
# EXPLORADOR TABULAR DE DATOS
# ==============================================================================
st.divider()
st.subheader("📋 Registros Filtrados")

columnas_mostrar = [
    "REGION", "GLOSA_SSS", "ESTABLECIMIENTO", "AREA_FUNCIONAL",
    "INDICE_OCUPACIONAL", "NUMERO_EGRESOS", "DIAS_ESTADA", "LETALIDAD"
]
columnas_existentes = [c for c in columnas_mostrar if c in df_filtrado.columns]

st.dataframe(df_filtrado[columnas_existentes], use_container_width=True)

# Pie de página institucional
st.markdown("---")
st.markdown(
    "<div style='text-align: right; color: gray; font-size: 0.85em;'>"
    "Proyecto desarrollado por: Kevin Oyarzún, Manuel Cárdena, Daniela Vera | Taller de Programación II - Universidad San Sebastián"
    "</div>",
    unsafe_allow_html=True
)
