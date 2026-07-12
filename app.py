import streamlit as st
import pandas as pd
from src.procesamiento import procesar_tp_completo, convertir_df_a_excel
from src.graficos import (generar_grafico_dias, generar_grafico_tiempos, 
                          generar_grafico_calificaciones, generar_grafico_preguntas)

st.set_page_config(
    page_title="Gestión de TPs - Química General",
    page_icon="🧪",
    layout="wide"
)

# Inicialización de variables persistentes en la sesión
if 'datos_procesados' not in st.session_state: st.session_state['datos_procesados'] = False
if 'df_informe_tp' not in st.session_state: st.session_state['df_informe_tp'] = None
if 'df_gen_cond' not in st.session_state: st.session_state['df_gen_cond'] = None
if 'df_gen_eval' not in st.session_state: st.session_state['df_gen_eval'] = None
if 'df_master' not in st.session_state: st.session_state['df_master'] = None
if 'meta_curso' not in st.session_state: st.session_state['meta_curso'] = {}

# =============================================================================
# FUNCIONES AUXILIARES PARA ESTILADO CONDICIONAL DE TABLAS (PANDAS STYLER)
# =============================================================================
def estilar_tabla_tp(df):
    """Aplica formato de colores a la tabla de cumplimiento individual."""
    def color_evaluacion(val):
        try:
            v = float(val)
            return 'color: #2a9d8f; font-weight: bold;' if v >= 30 else 'color: #e76f51; font-weight: bold;'
        except:
            return ''
            
    def color_condicion(val):
        if val == 'Cumple':
            return 'background-color: #d4edda; color: #155724; font-weight: bold;'
        elif val in ['No asistencia', 'No evaluación']:
            return 'background-color: #f8d7da; color: #721c24; font-weight: bold;'
        return ''
        
    styler = df.style.map(color_evaluacion, subset=['Evaluación'])
    styler = styler.map(color_condicion, subset=['Condición'])
    return styler

def estilar_planilla_general(df):
    """Aplica formato de colores a las columnas dinámicas de condición en el historial."""
    def color_condicion(val):
        if val == 'Cumple':
            return 'background-color: #d4edda; color: #155724; font-weight: bold;'
        elif val in ['No asistencia', 'No evaluación']:
            return 'background-color: #f8d7da; color: #721c24; font-weight: bold;'
        return ''
    
    cols_condicion = [c for c in df.columns if 'Condición' in str(c)]
    styler = df.style
    if cols_condicion:
        styler = styler.map(color_condicion, subset=cols_condicion)
    return styler


# =============================================================================
# INTERFAZ GRÁFICA - PESTAÑAS
# =============================================================================
st.title("🧪 Sistema de Gestión de TPs - Química General")
st.markdown("---")

tab_inicio, tab_adjuntar, tab_resultados = st.tabs([
    "🏠 Inicio / Instructivo", 
    "📂 Adjuntar Datos", 
    "📊 Presentación de Resultados"
])

# --- PESTAÑA 1: INICIO / INSTRUCTIVO (NUEVA: DISEÑADA AL DETALLE) ---
with tab_inicio:
    st.header("📖 Instructivo de Uso de la Aplicación")
    st.markdown("""
    Esta aplicación web permite centralizar, evaluar y graficar el desempeño de los alumnos en los Trabajos Prácticos de **Química General**. A partir de las planillas crudas extraídas de tu entorno virtual, el sistema genera reportes listos para descargar y dashboards visuales interactivos.
    
    ### 🛠️ Flujo de Trabajo en 3 Pasos:
    
    1. **Configura el Curso**: Ve a la pestaña **'Adjuntar Datos'** e ingresa la Carrera, Comisión, Año y el TP actual que deseas procesar (del 1 al 7).
    2. **Carga los Archivos**:
        * **Asistencias**: Archivo `.csv` o `.xlsx` exportado del registro de asistencia. El sistema reconocerá la columna **'P'** como presencia (1) o ausencia (0).
        * **Evaluaciones**: Archivo `.csv` o `.xlsx` de calificaciones de Moodle. El sistema analizará los tiempos, fechas de realización y el puntaje por cada pregunta de manera dinámica.
        * **Grupos**: Archivo `.xlsx` donde cada columna representa un grupo y contiene los nombres de sus respectivos integrantes.
        * **Planilla General (Opcional)**: Si ya has evaluado TPs anteriores este año, selecciona la opción para adjuntar tu archivo `Planilla_General.xlsx` para acoplar la nueva información.
    3. **Genera y Analiza**: Haz clic en **'Generar Resultados'** para desbloquear el tablero en la pestaña **'Presentación de Resultados'**. Allí podrás ver el listado de condiciones por alumno, los gráficos interactivos de rendimiento y descargar los Excel finales actualizados.
    
    ---
    *Desarrollado con Streamlit y Pandas para optimizar la gestión docente.*
    """)
    st.info("💡 Dirígete a la pestaña **'Adjuntar Datos'** para comenzar el procesamiento de las planillas.")

# --- PESTAÑA 2: ADJUNTAR DATOS ---
with tab_adjuntar:
    st.header("📂 Configuración del Curso y Carga de Planillas")
    st.subheader("1. Información del Curso")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        carrera = st.selectbox("Seleccione la Carrera:", ["Industrial", "Eléctrica", "Civil", "Mecánica"])
    with col2:
        comision = st.selectbox("Comisión:", ["Única"], disabled=True) if carrera == "Eléctrica" else st.selectbox("Comisión:", ["A", "B"])
    with col3:
        año = st.number_input("Año de Cursado:", min_value=2020, max_value=2040, value=2026)
    with col4:
        num_tp = st.slider("Número de Trabajo Práctico (TP):", min_value=1, max_value=7, value=3)

    st.markdown("---")
    st.subheader("2. Carga de Archivos")
    
    tiene_general = st.radio(
        "¿Posee un archivo 'Planilla_General.xlsx' de TPs anteriores?",
        ["No, crear una planilla nueva desde cero", "Sí, deseo adjuntar una planilla existente"], index=0
    )
    
    archivo_general = st.file_uploader("Adjuntar Planilla_General.xlsx:", type=["xlsx"]) if tiene_general == "Sí, deseo adjuntar una planilla existente" else None
    
    st.markdown("#### Cargar archivos del TP actual")
    c_asist, c_eval, c_grup = st.columns(3)
    
    with c_asist: archivo_asistencia = st.file_uploader("1. Planilla de Asistencias:", type=["csv", "xlsx"])
    with c_eval: archivo_evaluacion = st.file_uploader("2. Planilla de Evaluaciones:", type=["csv", "xlsx"])
    with c_grup: archivo_grupos = st.file_uploader("3. Planilla de Grupos:", type=["xlsx"])

    st.markdown("---")
    
    archivos_listos = archivo_asistencia and archivo_evaluacion and archivo_grupos
    if archivos_listos:
        if st.button("🚀 Generar Resultados", type="primary"):
            with st.spinner("Procesando datos matemáticos y modelando gráficos interactivos..."):
                df_inf, df_g_cond, df_g_eval, df_mst = procesar_tp_completo(
                    archivo_asistencia, archivo_evaluacion, archivo_grupos, archivo_general, f"TP{num_tp}"
                )
                
                st.session_state['df_informe_tp'] = df_inf
                st.session_state['df_gen_cond'] = df_g_cond
                st.session_state['df_gen_eval'] = df_g_eval
                st.session_state['df_master'] = df_mst
                st.session_state['meta_curso'] = {"carrera": carrera, "comision": comision, "año": año, "tp": f"TP{num_tp}"}
                st.session_state['datos_procesados'] = True
                
            st.success("🎉 ¡Resultados generados con éxito! Dirígete a la pestaña 'Presentación de Resultados'.")
    else:
        st.warning("⚠️ Para habilitar el botón, debes adjuntar las planillas de Asistencias, Evaluaciones y Grupos.")

# --- PESTAÑA 3: PRESENTACIÓN DE RESULTADOS ---
with tab_resultados:
    st.header("📊 Tablero de Resultados e Informes")
    
    if not st.session_state['datos_procesados']:
        st.info("ℹ️ No hay datos para mostrar todavía. Por favor, configura y procesa tus archivos en la pestaña **'Adjuntar Datos'**.")
    else:
        meta = st.session_state['meta_curso']
        st.subheader(f"📋 Resumen para: {meta['carrera']} - Comisión {meta['comision']} ({meta['año']}) | {meta['tp']}")
        
        col_down1, col_down2 = st.columns(2)
        with col_down1:
            data_excel_tp = convertir_df_a_excel(st.session_state['df_informe_tp'])
            st.download_button(
                label=f"📥 Descargar Informe {meta['tp']}.xlsx",
                data=data_excel_tp,
                file_name=f"Informe_{meta['tp']}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        with col_down2:
            data_excel_gen = convertir_df_a_excel(st.session_state['df_gen_cond'], estructurado_general=True, df_evals=st.session_state['df_gen_eval'])
            st.download_button(
                label="📥 Descargar Planilla_General_Actualizada.xlsx",
                data=data_excel_gen,
                file_name="Planilla_General.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
        st.markdown("---")
        
        # --- a. Tabla de Cumplimiento por Alumno ---
        st.markdown("### 👥 a. Tabla de Cumplimiento de Condiciones por Alumno")
        # NUEVO: Mostramos la tabla estilizada condicionalmente con colores rojo/verde
        df_tp_estilado = estilar_tabla_tp(st.session_state['df_informe_tp'])
        st.dataframe(df_tp_estilado, use_container_width=True)
        
        st.markdown("---")
        
        # --- b y c. Gráficas Temporales ---
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.markdown("### 📅 b. Evaluaciones Realizadas según el Día Disponible")
            fig_dias = generar_grafico_dias(st.session_state['df_master'])
            if fig_dias: st.plotly_chart(fig_dias, use_container_width=True)
            else: st.info("No hay datos de fecha disponibles en la planilla.")
            
        with col_g2:
            st.markdown("### ⏱️ c. Intentos en Función de la Duración de la Evaluación")
            fig_tiempos = generar_grafico_tiempos(st.session_state['df_master'])
            if fig_tiempos: st.plotly_chart(fig_tiempos, use_container_width=True)
            else: st.info("No hay datos de duración disponibles en la planilla.")
            
        st.markdown("---")
        
        # --- d y e. Gráficas Académicas ---
        col_g3, col_g4 = st.columns(2)
        with col_g3:
            st.markdown("### 📈 d. Distribución General de las Calificaciones Finales")
            fig_calif = generar_grafico_calificaciones(st.session_state['df_master'])
            st.plotly_chart(fig_calif, use_container_width=True)
            
        with col_g4:
            st.markdown("### 🧩 e. Análisis de Rendimiento por Pregunta del TP")
            fig_preguntas = generar_grafico_preguntas(st.session_state['df_master'])
            if fig_preguntas: st.plotly_chart(fig_preguntas, use_container_width=True)
            else: st.info("No se detectaron columnas con el formato de preguntas de Moodle.")
            
        st.markdown("---")
        
        # --- f. Tabla Resumen General Acumulativa ---
        st.markdown("### 🗃️ f. Tabla Resumen General de todos los TPs (Historial)")
        st.markdown("#### Vista de Condiciones de TPs anteriores y actual:")
        # NUEVO: Aplicamos colores rojo/verde a las columnas de condición de todos los TPs acumulados
        df_gen_estilado = estilar_planilla_general(st.session_state['df_gen_cond'])
        st.dataframe(df_gen_estilado, use_container_width=True)