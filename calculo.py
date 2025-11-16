<<<<<<< HEAD
import pandas as pd
import numpy as np
import os
import json

PATH_OUTPUT_FOLDER = "resultados"
PATH_RAW_DATA_CSV = os.path.join(PATH_OUTPUT_FOLDER, "dados_brutos_coletados_zonal.csv")
PATH_FINAL_CSV = os.path.join(PATH_OUTPUT_FOLDER, "resultados_finais_viabilidade_zonal.csv") 

mapbiomas_scores = {
    15: 10, 21: 8, 18: 6, 19: 6, 41: 6, 39: 6, 20: 6, 40: 6, 62: 6, 36: 5,
    46: 5, 47: 5, 35: 5, 48: 5, 3: 2, 4: 2, 10: 2, 12: 2, 9: 4, 49: 1, 50: 1,
    25: 1, 22: 1, 24: 0, 30: 0, 75: 0, 23: 0, 29: 0, 32: 0, 5: 0, 6: 0, 11: 0,
    26: 0, 33: 0, 31: 0, 27: 0
}

PESOS_WSM = {
    "vento": 0.40,
    "dist_rede": 0.25,
    "uso_solo": 0.20, 
    "declividade": 0.10,
    "conservacao": 0.05
}

def normalizar(valor, min_val, max_val, inverter=False):
    """Normaliza um valor para uma escala de 0 a 10."""
    if valor < min_val: valor = min_val
    if valor > max_val: valor = max_val
    if max_val == min_val: return 0 if inverter else 10
    
    if inverter: 
        valor_normalizado = 1 - ((valor - min_val) / (max_val - min_val))
    else: 
        valor_normalizado = (valor - min_val) / (max_val - min_val)
    
    return valor_normalizado * 10 

def calcular_nota_conservacao_zonal(json_string):
    """
    Calcula uma nota proporcional (0-10) com base nos percentuais
    de interseção das áreas de conservação (PI, US, Nenhuma).
    """
    try:
        if isinstance(json_string, str):
            dados = json.loads(json_string)
        else:
            dados = json_string
            
        pct_pi = dados.get("Proteção Integral", 0)
        pct_us = dados.get("Uso Sustentável", 0)
        pct_nenhuma = dados.get("Nenhuma", 100)
        
        nota_ponderada = (pct_nenhuma * 10) + (pct_us * 3) + (pct_pi * 0)
        return nota_ponderada / 100.0 
        
    except Exception:
        return 0

if __name__ == "__main__":
    
    try:
        df = pd.read_csv(PATH_RAW_DATA_CSV, sep=';', decimal=',')
        
        colunas_veto = ['pct_intersecao_urbana', 'dist_urbana_bruto_km']
        if not all(col in df.columns for col in colunas_veto):
            print("\nERRO: Colunas de veto essenciais (ex: 'pct_intersecao_urbana') não foram encontradas.")
            print("Por favor, execute a 'Etapa 1' primeiro para gerar este arquivo.")
            exit()
            
    except FileNotFoundError:
        print(f"ERRO: Arquivo de dados brutos '{PATH_RAW_DATA_CSV}' não encontrado.")
        exit()
    except Exception as e:
        print(f"ERRO ao ler o arquivo CSV: {e}")
        exit()

    df['nota_vento'] = df['vento_bruto_ms'].apply(lambda x: normalizar(x, 0, 7.56)) 
    df['nota_declive'] = df['declive_bruto_graus'].apply(lambda x: normalizar(x, 0, 15, inverter=True))
    df['nota_uso_solo'] = df['solo_bruto_codigo'].astype(int).map(mapbiomas_scores).fillna(0)
    df['nota_conservacao'] = df['restricao_dados_json'].apply(calcular_nota_conservacao_zonal)
    df['nota_dist_rede'] = (df['dist_rede_bruto_km'] * 1000).apply(lambda x: normalizar(x, 0, 150000, inverter=True))
    
    NOVO_BUFFER_KM = 2.0
    
    condicoes_veto = [
        (df['pct_intersecao_urbana'] > 50),  
        (df['dist_urbana_bruto_km'] < NOVO_BUFFER_KM),    
        (df['nota_uso_solo'] == 0)          
    ]
    
    razoes_veto = [
        "VETO: Interseção > 50% (GPKG)",
        f"VETO: Buffer {NOVO_BUFFER_KM}km (GPKG)", 
        "VETO: Uso do Solo (MapBiomas)"
    ]
    
    df['motivo_veto'] = np.select(condicoes_veto, razoes_veto, default="Aprovado")
    
    veto_total = (df['motivo_veto'] != "Aprovado")

    df['indice_final'] = (
        df['nota_vento'] * PESOS_WSM["vento"] +
        df['nota_dist_rede'] * PESOS_WSM["dist_rede"] +
        df['nota_uso_solo'] * PESOS_WSM["uso_solo"] +
        df['nota_declive'] * PESOS_WSM["declividade"] +
        df['nota_conservacao'] * PESOS_WSM["conservacao"]
    )
    
    df.loc[veto_total, 'indice_final'] = 0
    
    df.loc[df['indice_final'] > 10, 'indice_final'] = 10
    df['indice_final'] = df['indice_final'].round(2)

    colunas_principais = ['id_ponto', 'latitude_wgs84', 'longitude_wgs84', 'indice_final', 
                          'motivo_veto', 
                          'nota_vento', 'nota_dist_rede', 'nota_declive', 'nota_uso_solo', 
                          'nota_conservacao']
    
    colunas_brutas = [col for col in df.columns if col not in colunas_principais]
    df_final = df[colunas_principais + colunas_brutas]

    df_final.to_csv(PATH_FINAL_CSV, index=False, sep=';', decimal=',')
    
=======
import pandas as pd
import numpy as np
import os
import json

PATH_OUTPUT_FOLDER = "resultados"
PATH_RAW_DATA_CSV = os.path.join(PATH_OUTPUT_FOLDER, "dados_brutos_coletados_zonal.csv")
PATH_FINAL_CSV = os.path.join(PATH_OUTPUT_FOLDER, "resultados_finais_viabilidade_zonal.csv") 

mapbiomas_scores = {
    15: 10, 21: 8, 18: 6, 19: 6, 41: 6, 39: 6, 20: 6, 40: 6, 62: 6, 36: 5,
    46: 5, 47: 5, 35: 5, 48: 5, 3: 2, 4: 2, 10: 2, 12: 2, 9: 4, 49: 1, 50: 1,
    25: 1, 22: 1, 24: 0, 30: 0, 75: 0, 23: 0, 29: 0, 32: 0, 5: 0, 6: 0, 11: 0,
    26: 0, 33: 0, 31: 0, 27: 0
}

PESOS_WSM = {
    "vento": 0.40,
    "dist_rede": 0.25,
    "uso_solo": 0.20, 
    "declividade": 0.10,
    "conservacao": 0.05
}

def normalizar(valor, min_val, max_val, inverter=False):
    """Normaliza um valor para uma escala de 0 a 10."""
    if valor < min_val: valor = min_val
    if valor > max_val: valor = max_val
    if max_val == min_val: return 0 if inverter else 10
    
    if inverter: 
        valor_normalizado = 1 - ((valor - min_val) / (max_val - min_val))
    else: 
        valor_normalizado = (valor - min_val) / (max_val - min_val)
    
    return valor_normalizado * 10 

def calcular_nota_conservacao_zonal(json_string):
    """
    Calcula uma nota proporcional (0-10) com base nos percentuais
    de interseção das áreas de conservação (PI, US, Nenhuma).
    """
    try:
        if isinstance(json_string, str):
            dados = json.loads(json_string)
        else:
            dados = json_string
            
        pct_pi = dados.get("Proteção Integral", 0)
        pct_us = dados.get("Uso Sustentável", 0)
        pct_nenhuma = dados.get("Nenhuma", 100)
        
        nota_ponderada = (pct_nenhuma * 10) + (pct_us * 3) + (pct_pi * 0)
        return nota_ponderada / 100.0 
        
    except Exception:
        return 0

if __name__ == "__main__":
    
    try:
        df = pd.read_csv(PATH_RAW_DATA_CSV, sep=';', decimal=',')
        
        colunas_veto = ['pct_intersecao_urbana', 'dist_urbana_bruto_km']
        if not all(col in df.columns for col in colunas_veto):
            print("\nERRO: Colunas de veto essenciais (ex: 'pct_intersecao_urbana') não foram encontradas.")
            print("Por favor, execute a 'Etapa 1' primeiro para gerar este arquivo.")
            exit()
            
    except FileNotFoundError:
        print(f"ERRO: Arquivo de dados brutos '{PATH_RAW_DATA_CSV}' não encontrado.")
        exit()
    except Exception as e:
        print(f"ERRO ao ler o arquivo CSV: {e}")
        exit()

    df['nota_vento'] = df['vento_bruto_ms'].apply(lambda x: normalizar(x, 0, 7.56)) 
    df['nota_declive'] = df['declive_bruto_graus'].apply(lambda x: normalizar(x, 0, 15, inverter=True))
    df['nota_uso_solo'] = df['solo_bruto_codigo'].astype(int).map(mapbiomas_scores).fillna(0)
    df['nota_conservacao'] = df['restricao_dados_json'].apply(calcular_nota_conservacao_zonal)
    df['nota_dist_rede'] = (df['dist_rede_bruto_km'] * 1000).apply(lambda x: normalizar(x, 0, 150000, inverter=True))
    
    NOVO_BUFFER_KM = 2.0
    
    condicoes_veto = [
        (df['pct_intersecao_urbana'] > 50),  
        (df['dist_urbana_bruto_km'] < NOVO_BUFFER_KM),    
        (df['nota_uso_solo'] == 0)          
    ]
    
    razoes_veto = [
        "VETO: Interseção > 50% (GPKG)",
        f"VETO: Buffer {NOVO_BUFFER_KM}km (GPKG)", 
        "VETO: Uso do Solo (MapBiomas)"
    ]
    
    df['motivo_veto'] = np.select(condicoes_veto, razoes_veto, default="Aprovado")
    
    veto_total = (df['motivo_veto'] != "Aprovado")

    df['indice_final'] = (
        df['nota_vento'] * PESOS_WSM["vento"] +
        df['nota_dist_rede'] * PESOS_WSM["dist_rede"] +
        df['nota_uso_solo'] * PESOS_WSM["uso_solo"] +
        df['nota_declive'] * PESOS_WSM["declividade"] +
        df['nota_conservacao'] * PESOS_WSM["conservacao"]
    )
    
    df.loc[veto_total, 'indice_final'] = 0
    
    df.loc[df['indice_final'] > 10, 'indice_final'] = 10
    df['indice_final'] = df['indice_final'].round(2)

    colunas_principais = ['id_ponto', 'latitude_wgs84', 'longitude_wgs84', 'indice_final', 
                          'motivo_veto', 
                          'nota_vento', 'nota_dist_rede', 'nota_declive', 'nota_uso_solo', 
                          'nota_conservacao']
    
    colunas_brutas = [col for col in df.columns if col not in colunas_principais]
    df_final = df[colunas_principais + colunas_brutas]

    df_final.to_csv(PATH_FINAL_CSV, index=False, sep=';', decimal=',')
    
>>>>>>> a766db1 (upando arquivos)
    print(f"Processamento concluído. Resultados salvos em: {PATH_FINAL_CSV}")