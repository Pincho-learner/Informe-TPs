import pandas as pd
import numpy as np
import re
import io

def parsear_fecha_moodle(texto_fecha):
    if pd.isna(texto_fecha) or str(texto_fecha).strip() in ['-', '']:
        return pd.NaT
    texto = str(texto_fecha).lower().replace(' de ', ' ').strip()
    meses = {
        'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
        'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
    }
    try:
        partes = texto.split()
        dia = int(partes[0])
        mes_str = partes[1]
        anio = int(partes[2])
        hora_str = partes[3]
        mes_num = meses.get(mes_str, 1)
        return pd.to_datetime(f"{anio}-{mes_num:02d}-{dia:02d} {hora_str}")
    except:
        return pd.NaT

def parsear_duracion_moodle(texto_duracion):
    if pd.isna(texto_duracion) or str(texto_duracion).strip() in ['-', '']:
        return np.nan
    texto = str(texto_duracion).lower()
    buscar_horas = re.search(r'(\d+)\s*hora', texto)
    buscar_minutos = re.search(r'(\d+)\s*minuto', texto)
    buscar_segundos = re.search(r'(\d+)\s*segundo', texto)
    
    h = int(buscar_horas.group(1)) if buscar_horas else 0
    m = int(buscar_minutos.group(1)) if buscar_minutos else 0
    s = int(buscar_segundos.group(1)) if buscar_segundos else 0
    return (h * 60) + m + (s / 60)

def leer_archivo_streamlit(uploaded_file, buscar_palabra=None):
    if uploaded_file.name.endswith('.csv'):
        bytes_data = uploaded_file.getvalue()
        try:
            df_raw = pd.read_csv(io.BytesIO(bytes_data), header=None, sep=None, engine='python')
        except:
            df_raw = pd.read_csv(io.BytesIO(bytes_data), header=None, encoding='latin1', sep=None, engine='python')
        
        uploaded_file.seek(0)
        if buscar_palabra:
            try:
                header_row = df_raw[df_raw.apply(lambda r: r.astype(str).str.contains(buscar_palabra, case=False, na=False).any(), axis=1)].index[0]
                try: df = pd.read_csv(uploaded_file, skiprows=header_row, sep=None, engine='python')
                except: 
                    uploaded_file.seek(0)
                    df = pd.read_csv(uploaded_file, skiprows=header_row, encoding='latin1', sep=None, engine='python')
            except:
                df = pd.read_csv(uploaded_file, sep=None, engine='python')
        else:
            df = pd.read_csv(uploaded_file, sep=None, engine='python')
    else:
        bytes_data = uploaded_file.getvalue()
        if buscar_palabra:
            try:
                df_raw = pd.read_excel(io.BytesIO(bytes_data), header=None)
                header_row = df_raw[df_raw.apply(lambda r: r.astype(str).str.contains(buscar_palabra, case=False, na=False).any(), axis=1)].index[0]
                df = pd.read_excel(io.BytesIO(bytes_data), header=header_row)
            except:
                df = pd.read_excel(io.BytesIO(bytes_data))
        else:
            df = pd.read_excel(io.BytesIO(bytes_data))
            
    df.columns = df.columns.astype(str).str.strip()
    return df

def procesar_tp_completo(archivo_asist, archivo_eval, archivo_grup, archivo_gen_cargado, nombre_tp):
    df_asist = leer_archivo_streamlit(archivo_asist, buscar_palabra='Apellido')
    df_eval = leer_archivo_streamlit(archivo_eval, buscar_palabra='Apellido')
    df_grupos = leer_archivo_streamlit(archivo_grup)

    for df in [df_asist, df_eval]:
        if 'Apellido(s)' in df.columns: df['Apellido(s)'] = df['Apellido(s)'].astype(str).str.strip()
        if 'Nombre' in df.columns: df['Nombre'] = df['Nombre'].astype(str).str.strip()

    df_asist.rename(columns={'P': 'Asistencia'}, inplace=True)
    df_asist['Asistencia'] = df_asist['Asistencia'].astype(str).apply(lambda x: 1 if '1' in x else 0) if 'Asistencia' in df_asist.columns else 0

    col_calif = [col for col in df_eval.columns if 'calificaci' in col.lower()]
    if col_calif:
        col_nota = col_calif[0]
        df_eval[col_nota] = df_eval[col_nota].astype(str).str.strip().str.replace(',', '.').str.replace('-', '0')
        df_eval['Calificación_Num'] = pd.to_numeric(df_eval[col_nota], errors='coerce').fillna(0)
    else:
        df_eval['Calificación_Num'] = 0

    if 'Comenzado el' in df_eval.columns:
        df_eval['Fecha_Inicio_Real'] = df_eval['Comenzado el'].apply(parsear_fecha_moodle)
    if 'Tiempo requerido' in df_eval.columns:
        df_eval['Tiempo_Minutos_Num'] = df_eval['Tiempo requerido'].apply(parsear_duracion_moodle)

    lista_grupos = []
    for col in df_grupos.columns:
        alumnos_grupo = df_grupos[col].dropna().tolist()
        for alumno in alumnos_grupo:
            lista_grupos.append({'Nombre Completo Grupo': str(alumno).strip().lower(), 'Grupo': col})
    df_grupos_plano = pd.DataFrame(lista_grupos)

    df_master = pd.merge(df_asist, df_eval, on=['Apellido(s)', 'Nombre'], how='left')
    df_master['Calificación_Num'] = df_master['Calificación_Num'].fillna(0)

    def encontrar_grupo(row):
        nombre_ap = f"{row['Nombre']} {row['Apellido(s)']}".lower()
        for idx, r in df_grupos_plano.iterrows():
            n_grupo = r['Nombre Completo Grupo']
            if set(nombre_ap.replace(',', '').split()).issubset(set(n_grupo.replace(',', '').split())):
                return r['Grupo']
        return "Sin Grupo"

    df_master['Grupo'] = df_master.apply(encontrar_grupo, axis=1)

    def determinar_condicion(row):
        if row['Asistencia'] != 1: return "No asistencia"
        elif row['Calificación_Num'] < 30: return "No evaluación"
        else: return "Cumple"

    df_master['Condición'] = df_master.apply(determinar_condicion, axis=1)

    # Preparación del informe por TP
    df_informe_tp = df_master[['Apellido(s)', 'Nombre', 'Grupo', 'Asistencia', 'Calificación_Num', 'Condición']].copy()
    df_informe_tp.rename(columns={'Calificación_Num': 'Evaluación'}, inplace=True)
    
    # NUEVO: Conversión de Asistencia a Presente/Ausente para mayor claridad visual
    df_informe_tp['Asistencia'] = df_informe_tp['Asistencia'].map({1: 'Presente', 0: 'Ausente'})
    
    df_informe_tp.sort_values(by=['Grupo', 'Apellido(s)'], inplace=True)

    df_nueva_info = df_informe_tp[['Apellido(s)', 'Nombre', 'Grupo', 'Condición', 'Evaluación']].copy()
    
    if archivo_gen_cargado is not None:
        try:
            df_gen_cond = pd.read_excel(archivo_gen_cargado, sheet_name='Condiciones')
            df_gen_eval = pd.read_excel(archivo_gen_cargado, sheet_name='Evaluaciones')
            
            if f'Condición {nombre_tp}' in df_gen_cond.columns: df_gen_cond.drop(columns=[f'Condición {nombre_tp}'], inplace=True)
            if f'Evaluación {nombre_tp}' in df_gen_eval.columns: df_gen_eval.drop(columns=[f'Evaluación {nombre_tp}'], inplace=True)

            df_gen_cond = pd.merge(df_gen_cond, df_nueva_info[['Apellido(s)', 'Nombre', 'Grupo', 'Condición']], on=['Apellido(s)', 'Nombre', 'Grupo'], how='outer')
            df_gen_cond.rename(columns={'Condición': f'Condición {nombre_tp}'}, inplace=True)
            
            df_gen_eval = pd.merge(df_gen_eval, df_nueva_info[['Apellido(s)', 'Nombre', 'Grupo', 'Evaluación']], on=['Apellido(s)', 'Nombre', 'Grupo'], how='outer')
            df_gen_eval.rename(columns={'Evaluación': f'Evaluación {nombre_tp}'}, inplace=True)
        except:
            df_gen_cond = df_nueva_info[['Apellido(s)', 'Nombre', 'Grupo', 'Condición']].rename(columns={'Condición': f'Condición {nombre_tp}'})
            df_gen_eval = df_nueva_info[['Apellido(s)', 'Nombre', 'Grupo', 'Evaluación']].rename(columns={'Evaluación': f'Evaluación {nombre_tp}'})
    else:
        df_gen_cond = df_nueva_info[['Apellido(s)', 'Nombre', 'Grupo', 'Condición']].copy()
        df_gen_cond.rename(columns={'Condición': f'Condición {nombre_tp}'}, inplace=True)
        df_gen_eval = df_nueva_info[['Apellido(s)', 'Nombre', 'Grupo', 'Evaluación']].copy()
        df_gen_eval.rename(columns={'Evaluación': f'Evaluación {nombre_tp}'}, inplace=True)

    return df_informe_tp, df_gen_cond, df_gen_eval, df_master

def convertir_df_a_excel(df, estructurado_general=False, df_evals=None):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        if estructurado_general:
            df.to_excel(writer, sheet_name='Condiciones', index=False)
            if df_evals is not None:
                df_evals.to_excel(writer, sheet_name='Evaluaciones', index=False)
        else:
            df.to_excel(writer, sheet_name='Resultados', index=False)
    return output.getvalue()