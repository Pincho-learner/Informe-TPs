import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import re

def generar_grafico_dias(df_master):
    if 'Fecha_Inicio_Real' not in df_master.columns:
        return None
    df_valid = df_master.dropna(subset=['Fecha_Inicio_Real'])
    if df_valid.empty:
        return None
    
    df_valid['Día'] = df_valid['Fecha_Inicio_Real'].dt.strftime('%d-%b')
    df_counts = df_valid['Día'].value_counts().sort_index().reset_index()
    df_counts.columns = ['Fecha', 'Cantidad de Alumnos']
    
    fig = px.bar(
        df_counts, x='Fecha', y='Cantidad de Alumnos',
        title="Evaluaciones Realizadas según el Día Disponible",
        labels={'Cantidad de Alumnos': 'Número de Alumnos', 'Fecha': 'Día del Intento'},
        color_discrete_sequence=['#4ea8de']
    )
    # NUEVO: Centrado explícito del título
    fig.update_layout(
        template="simple_white", 
        title_x=0.5,
        title_xanchor='center'
    )
    return fig

def generar_grafico_tiempos(df_master):
    if 'Tiempo_Minutos_Num' not in df_master.columns:
        return None
    df_valid = df_master.dropna(subset=['Tiempo_Minutos_Num'])
    if df_valid.empty:
        return None
    
    intervalos = np.arange(0, df_valid['Tiempo_Minutos_Num'].max() + 2, 2)
    conteos, bordes = np.histogram(df_valid['Tiempo_Minutos_Num'], bins=intervalos)
    centros = bordes[:-1] + 1
    
    df_curva = pd.DataFrame({'Tiempo Promedio (Minutos)': centros, 'Cantidad de Intentos': conteos})
    
    fig = px.line(
        df_curva, x='Tiempo Promedio (Minutos)', y='Cantidad de Intentos',
        title="Intentos en Función de la Duración de la Evaluación",
        markers=True,
        color_discrete_sequence=['#7209b7']
    )
    # NUEVO: Centrado explícito del título
    fig.update_layout(
        template="simple_white", 
        title_x=0.5,
        title_xanchor='center'
    )
    fig.update_traces(line=dict(width=3))
    return fig

def generar_grafico_calificaciones(df_master):
    fig = px.histogram(
        df_master, x='Calificación_Num',
        range_x=[0, 100],
        title="Distribución General de las Calificaciones Finales",
        labels={'Calificación_Num': 'Calificación obtenida (/100)', 'count': 'Cantidad de Alumnos'},
        color_discrete_sequence=['#4cc9f0']
    )
    # NUEVO: Centrado del título y agrupamiento de barras de 5 en 5 puntos (xbins)
    fig.update_layout(
        template="simple_white", 
        title_x=0.5, 
        title_xanchor='center',
        yaxis_title="Cantidad de Alumnos"
    )
    fig.update_traces(
        xbins=dict(start=0, end=100, size=5),
        marker_line_color='black', 
        marker_line_width=1, 
        opacity=0.85
    )
    return fig

def generar_grafico_preguntas(df_master):
    preguntas_cols = [col for col in df_master.columns if col.startswith('P. ') or re.match(r'^Q\d+', str(col))]
    if not preguntas_cols:
        return None
        
    data_list = []
    for col in preguntas_cols:
        nombre_pregunta = col.split('/')[0].strip()
        try: max_nota = float(col.split('/')[1].replace(',', '.'))
        except: max_nota = df_master[col].replace('-', 0).astype(str).str.replace(',', '.').astype(float).max()
        
        notas_num = df_master[col].replace('-', 0).astype(str).str.replace(',', '.').astype(float).fillna(0)
        
        correctas = (notas_num >= max_nota * 0.95).sum()
        incorrectas = (notas_num == 0).sum()
        parciales = len(notas_num) - correctas - incorrectas
        
        data_list.append({'Pregunta': nombre_pregunta, 'Estado': 'Correcta', 'Alumnos': correctas})
        data_list.append({'Pregunta': nombre_pregunta, 'Estado': 'Parcial / Error', 'Alumnos': parciales})
        data_list.append({'Pregunta': nombre_pregunta, 'Estado': 'Incorrecta / Vacía', 'Alumnos': incorrectas})
        
    df_plot = pd.DataFrame(data_list)
    
    fig = px.bar(
        df_plot, x='Pregunta', y='Alumnos', color='Estado',
        title="Análisis de Rendimiento por Pregunta del TP",
        barmode='group',
        color_discrete_map={
            'Correcta': '#2a9d8f',
            'Parcial / Error': '#f4a261',
            'Incorrecta / Vacía': '#e76f51'
        }
    )
    # NUEVO: Centrado explícito del título
    fig.update_layout(
        template="simple_white", 
        title_x=0.5,
        title_xanchor='center',
        yaxis_title="Cantidad de Alumnos"
    )
    return fig