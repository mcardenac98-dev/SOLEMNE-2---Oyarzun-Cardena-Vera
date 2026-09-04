import matplotlib.pyplot as plt
import pandas as pd
import requests
import streamlit as st

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA
# ==========================================
st.set_page_config(
    page_title="Dashboard REM20 - Salud Chile", page_icon="🏥", layout="wide"
)

st.title("🏥 Indicadores Hospitalarios por Región y Establecimiento (REM20)")
st.markdown(
    "Monitoreo interactivo de la Red Pública Hospitalaria con datos de"
    " **datos.gob.cl** (MINSAL)."
)


# ==========================================
# 2. CARGA DE DATOS Y ASIGNACIÓN REGIONAL
# ==========================================
@st.cache_data(show_spinner=False)
def cargar_datos_chile():
  url = "https://datos.gob.cl/api/3/action/datastore_search?resource_id=657cc933-eac8-4bfc-b004-c4d6dcd988a8&limit=50000"
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
      )
  }

  try:
    respuesta = requests.get(url, headers=headers, timeout=25)
    if respuesta.status_code == 200:
      datos = respuesta.json()
      df = pd.DataFrame(datos["result"]["records"])

      # Limpieza de textos
      df["GLOSA_SSS"] = df["GLOSA_SSS"].astype(str).str.strip()
      df["ESTABLECIMIENTO"] = df["ESTABLECIMIENTO"].astype(str).str.strip()
      df["AREA_FUNCIONAL"] = df["AREA_FUNCIONAL"].astype(str).str.strip()

      # Mapeo inverso de Servicio a Región
      servicio_a_region = {}
      for region, lista_servicios in MAPA_REGIONES.items():
        for srv in lista_servicios:
          servicio_a_region[srv] = region

      df["REGION"] = df["GLOSA_SSS"].map(servicio_a_region).fillna("Otras")

      # Conversión de métricas numéricas
      columnas_num = [
          "DIAS_CAMAS_OCUPADAS",
          "DIAS_CAMAS_DISPONIBLES",
          "DIAS_ESTADA",
          "NUMERO_EGRESOS",
          "EGRESOS_FALLECIDOS",
          "INDICE_OCUPACIONAL",
          "LETALIDAD",
      ]
      for col in columnas_num:
        if col in df.columns:
          df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

      return df
    return pd.DataFrame()
  except Exception:
    return pd.DataFrame()


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

with st.spinner("Conectando y organizando datos territoriales..."):
  df_raw = cargar_datos_chile()

if df_raw.empty:
  st.error("No se pudo conectar a datos.gob.cl.")
  st.stop()

# ==========================================
# 3. FILTROS EN CASCADA (REGIÓN -> HOSPITAL)
# ==========================================
st.sidebar.header("🗺️ Filtros Territoriales")

# 1. Filtro Región
lista_regiones = ["Todas las Regiones"] + sorted(list(MAPA_REGIONES.keys()))
region_seleccionada = st.sidebar.selectbox("Seleccione Región:", lista_regiones)

# Filtrar según la región para alimentar el segundo selector
if region_seleccionada == "Todas las Regiones":
  df_por_region = df_raw
else:
  df_por_region = df_raw[df_raw["REGION"] == region_seleccionada]

# 2. Filtro Establecimiento (Comuna / Hospital)
establecimientos_disponibles = sorted(
    df_por_region["ESTABLECIMIENTO"].unique()
)
todos_los_hosp = st.sidebar.checkbox(
    "Incluir todos los establecimientos", value=True
)

if todos_los_hosp:
  hosp_sel = establecimientos_disponibles
else:
  hosp_sel = st.sidebar.multiselect(
      "Establecimientos / Hospitales:",
      options=establecimientos_disponibles,
      default=(
          establecimientos_disponibles[:3]
          if len(establecimientos_disponibles) >= 3
          else establecimientos_disponibles
      ),
  )

# 3. Filtro Área / Especialidad
areas_disponibles = sorted(df_raw["AREA_FUNCIONAL"].unique())
areas_sel = st.sidebar.multiselect(
    "Especialidad / Área Funcional:",
    options=areas_disponibles,
    default=areas_disponibles,
)
# Obtener especialidades disponibles únicamente para la región/establecimiento actual
especialidades_disponibles = sorted(df_region["AREA_FUNCIONAL"].dropna().unique().tolist())

# Multiselect que toma por defecto todas las especialidades válidas de esa región
especialidades_sel = st.sidebar.multiselect(
    "Especialidad / Área Funcional:",
    options=especialidades_disponibles,
    default=especialidades_disponibles[:5] if len(especialidades_disponibles) >= 5 else especialidades_disponibles
)

# Filtrar según la selección
if especialidades_sel:
    df_filtrado = df_region[df_region["AREA_FUNCIONAL"].isin(especialidades_sel)]
else:
    df_filtrado = df_region
# Aplicación final del filtro reactivo
df_filtrado = df_por_region[
    (df_por_region["ESTABLECIMIENTO"].isin(hosp_sel))
    & (df_por_region["AREA_FUNCIONAL"].isin(areas_sel))
]

# ==========================================
# 4. MÉTRICAS CLAVE
# ==========================================
st.subheader(f"📌 Resumen: {region_seleccionada}")
col1, col2, col3, col4 = st.columns(4)

total_registros = len(df_filtrado)
promedio_ocupacion = (
    df_filtrado["INDICE_OCUPACIONAL"].mean() if total_registros > 0 else 0
)
total_egresos = (
    int(df_filtrado["NUMERO_EGRESOS"].sum()) if total_registros > 0 else 0
)
letalidad_promedio = (
    df_filtrado["LETALIDAD"].mean() if total_registros > 0 else 0
)

col1.metric("Registros", f"{total_registros:,}")
col2.metric("Ocupación Camas", f"{promedio_ocupacion:.1f}%")
col3.metric("Total Egresos", f"{total_egresos:,}")
col4.metric("Letalidad Media", f"{letalidad_promedio:.1f}%")

st.markdown("---")

# ==========================================
# 5. VISUALIZACIÓN ANALÍTICA CON MATPLOTLIB
# ==========================================
st.subheader("📊 Visualización Gráfica")
tab1, tab2 = st.tabs(
    ["Ocupación por Establecimiento", "Egresos vs Días de Estada"]
)

with tab1:
  if not df_filtrado.empty:
    # Filtramos valores anómalos (porcentaje ocupacional entre 1% y 100%)
    df_ocupacion_valida = df_filtrado[
        (df_filtrado["INDICE_OCUPACIONAL"] > 0)
        & (df_filtrado["INDICE_OCUPACIONAL"] <= 100)
    ]

    resumen_hosp = (
        df_ocupacion_valida.groupby("ESTABLECIMIENTO")["INDICE_OCUPACIONAL"]
        .mean()
        .sort_values(ascending=False)
        .head(10)
        .sort_values(ascending=True)
    )

    fig1, ax1 = plt.subplots(figsize=(10, 5))
    barras = resumen_hosp.plot(kind="barh", color="#1f77b4", ax=ax1)
    ax1.set_title(
        "Top 10 Hospitales con Mayor Demanda y Ocupación (%)",
        fontsize=12,
        pad=10,
    )
    ax1.set_xlabel("Índice Ocupacional Promedio (%)")
    ax1.set_ylabel("Establecimiento")
    ax1.set_xlim(0, 105)
    ax1.grid(axis="x", linestyle="--", alpha=0.5)

    # Añadimos etiquetas numéricas en las barras para mayor claridad
    for p in ax1.patches:
      ax1.annotate(
          f"{p.get_width():.1f}%",
          (p.get_width() + 1, p.get_y() + 0.15),
          fontsize=9,
      )

    plt.tight_layout()
    st.pyplot(fig1)
  else:
    st.info("Sin registros para la selección actual.")

with tab2:
  if not df_filtrado.empty:
    # Removemos outliers extremos de días de estada para ver la correlación real
    p98_estada = df_filtrado["DIAS_ESTADA"].quantile(0.98)
    df_dispersion = df_filtrado[
        (df_filtrado["DIAS_ESTADA"] <= p98_estada)
        & (df_filtrado["NUMERO_EGRESOS"] > 0)
    ]

    fig2, ax2 = plt.subplots(figsize=(10, 5))
    ax2.scatter(
        df_dispersion["NUMERO_EGRESOS"],
        df_dispersion["DIAS_ESTADA"],
        alpha=0.45,
        color="#2ca02c",
        edgecolors="none",
        s=40,
    )
    ax2.set_title(
        "Relación entre Altas Clínicas (Egresos) y Días de Estada Acumulados",
        fontsize=12,
        pad=10,
    )
    ax2.set_xlabel("Número de Egresos")
    ax2.set_ylabel("Días de Estada Acumulados")
    ax2.grid(True, linestyle="--", alpha=0.4)
    plt.tight_layout()
    st.pyplot(fig2)
  else:
    st.info("Sin registros para la selección actual.")

# ==========================================
# 6. TABLA DETALLADA
# ==========================================
st.markdown("---")
st.subheader("📋 Registros Filtrados")
st.dataframe(
    df_filtrado[[
        "REGION",
        "GLOSA_SSS",
        "ESTABLECIMIENTO",
        "AREA_FUNCIONAL",
        "INDICE_OCUPACIONAL",
        "NUMERO_EGRESOS",
        "DIAS_ESTADA",
    ]],
    use_container_width=True,
)
# ==========================================
# 7. PIE DE PÁGINA / AUTORÍA
# ==========================================
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray; font-size: 0.9em;'>
        Proyecto desarrollado por: Kevin Oyarzun, Manuel Cárdena, Daniela Vera | Septiembre 2026<br>
        Taller de Programación II - Universidad San Sebastián
    </div>
    """,
    unsafe_allow_html=True,
)
