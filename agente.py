import os
import time
import json
import requests
import pandas as pd
import geopandas
import rasterio
import rasterstats
from tqdm import tqdm
from shapely.geometry import Point

PATH_GRID = "dados/RN_grid_quadrado.gpkg"
PATH_AREAS_URBANAS = "dados/RN_areas_urbanas.gpkg"
PATH_SUBESTACOES = "dados/RN.gpkg"
PATH_AREAS_CONSERVACAO = "dados/area_coservacao_RN.gpkg"
PATH_DECLIVE = "dados/declive_gray_RN.tif"
PATH_RASTER_USO_SOLO = "dados/solo_gray-RN.tif"
PATH_OUTPUT_FOLDER = "resultados"
PATH_RAW_DATA_CSV = os.path.join(PATH_OUTPUT_FOLDER, "dados_brutos_coletados_zonal.csv")

ANO_INICIO_NASA = 2020
ANO_FIM_NASA = 2024
NASA_PARAMETRO_VENTO = "WS50M"
NASA_PARAMETRO_SOLAR = "ALLSKY_SFC_SW_DWN"

def carregar_dados_geoespaciais():
    dados = {
        "grid": geopandas.read_file(PATH_GRID),
        "areas_urbanas": geopandas.read_file(PATH_AREAS_URBANAS),
        "subestacoes": geopandas.read_file(PATH_SUBESTACOES),
        "conservacao": geopandas.read_file(PATH_AREAS_CONSERVACAO),
    }

    crs_base = dados["grid"].crs

    for nome, camada in dados.items():
        if hasattr(camada, "crs") and camada.crs != crs_base:
            dados[nome] = camada.to_crs(crs_base)

    return dados

def obter_dados_nasa(lat, lon):
    data_inicio = f"{ANO_INICIO_NASA}0101"
    data_fim = f"{ANO_FIM_NASA}1231"

    url_base = "https://power.larc.nasa.gov/api/temporal/daily/point"
    parametros = {
        "parameters": f"{NASA_PARAMETRO_VENTO},{NASA_PARAMETRO_SOLAR}",
        "community": "re",
        "longitude": lon,
        "latitude": lat,
        "start": data_inicio,
        "end": data_fim,
        "format": "JSON"
    }

    def extrair_medias(resposta_json):
        resultados = {"vento": 0.0, "solar": 0.0}
        try:
            propriedades = resposta_json.get('properties', {})
            parametros_resp = propriedades.get('parameter', {})
            
            if NASA_PARAMETRO_VENTO in parametros_resp:
                valores_vento = parametros_resp[NASA_PARAMETRO_VENTO].values()
                valores_validos = [v for v in valores_vento if v > -90]
                if valores_validos:
                    resultados["vento"] = sum(valores_validos) / len(valores_validos)
            
            if NASA_PARAMETRO_SOLAR in parametros_resp:
                valores_solar = parametros_resp[NASA_PARAMETRO_SOLAR].values()
                valores_validos_solar = [v for v in valores_solar if v > -90]
                if valores_validos_solar:
                    resultados["solar"] = sum(valores_validos_solar) / len(valores_validos_solar)
                    
            return resultados
        except Exception:
            return resultados

    try:
        resposta = requests.get(url_base, params=parametros, timeout=30)
        resposta.raise_for_status() 
        return extrair_medias(resposta.json())
    except Exception:
        time.sleep(5) 
        try:
            resposta = requests.get(url_base, params=parametros, timeout=30)
            return extrair_medias(resposta.json())
        except Exception as erro:
            return {"vento": 0.0, "solar": 0.0} 

def calcular_intersecao_conservacao(geom_celula, gdf_conservacao, coluna_categoria='grupo'):
    estatisticas = {"Proteção Integral": 0.0, "Uso Sustentável": 0.0, "Nenhuma": 0.0}
    area_celula = geom_celula.area
    if area_celula == 0: return estatisticas
    uc_recortada = geopandas.clip(gdf_conservacao, geom_celula)
    if uc_recortada.empty:
        estatisticas["Nenhuma"] = 100.0
        return estatisticas
    uc_recortada['area_intersecao'] = uc_recortada.geometry.area
    area_por_grupo = uc_recortada.groupby(coluna_categoria)['area_intersecao'].sum()
    area_total_intersecao = 0.0
    for grupo, area in area_por_grupo.items():
        if grupo in estatisticas:
            porcentagem = (area / area_celula) * 100
            estatisticas[grupo] = round(porcentagem, 2)
            area_total_intersecao += area
    area_restante = max(0.0, area_celula - area_total_intersecao)
    estatisticas["Nenhuma"] = round((area_restante / area_celula) * 100, 2)
    return estatisticas

def calcular_percentual_urbano(geom_celula, gdf_urbano, area_celula):
    if area_celula == 0: return 0.0
    urbano_recortado = geopandas.clip(gdf_urbano, geom_celula)
    if urbano_recortado.empty: return 0.0
    area_intersecao = urbano_recortado.union_all().area
    return round((area_intersecao / area_celula) * 100, 2)

if __name__ == "__main__":

    if not os.path.exists(PATH_OUTPUT_FOLDER):
        os.makedirs(PATH_OUTPUT_FOLDER)

    cache_nasa_vento = {}
    cache_nasa_solar = {}
    
    if os.path.exists(PATH_RAW_DATA_CSV):
        try:
            df_cache = pd.read_csv(PATH_RAW_DATA_CSV, sep=';', decimal=',')
            
            if 'vento_bruto_ms' in df_cache.columns:
                cache_nasa_vento = pd.Series(
                    df_cache.vento_bruto_ms.values,
                    index=df_cache.id_ponto
                ).to_dict()
            
            if 'radiacao_solar_bruta' in df_cache.columns:
                cache_nasa_solar = pd.Series(
                    df_cache.radiacao_solar_bruta.values,
                    index=df_cache.id_ponto
                ).to_dict()

        except Exception as e:
            pass

    camadas = carregar_dados_geoespaciais()
    grid_wgs84 = camadas["grid"].to_crs("EPSG:4326")
    camadas["grid"]["centroide_wgs84"] = grid_wgs84.geometry.centroid
    camadas["grid"]["centroide_local"] = camadas["grid"].geometry.centroid
    
    uniao_urbana = camadas["areas_urbanas"].union_all()
    uniao_subestacoes = camadas["subestacoes"].union_all()
    
    filtro_pi = camadas["conservacao"]["grupo"] == "Proteção Integral"
    filtro_us = camadas["conservacao"]["grupo"] == "Uso Sustentável"
    conservacao_otimizada = geopandas.GeoDataFrame(
        [
            {'grupo': 'Proteção Integral', 'geometry': camadas["conservacao"][filtro_pi].union_all()},
            {'grupo': 'Uso Sustentável', 'geometry': camadas["conservacao"][filtro_us].union_all()}
        ], crs=camadas["grid"].crs
    ).dropna(subset=['geometry'])

    lista_resultados = []
    grid_original = camadas["grid"]
    grid_original['id_ponto_int'] = range(len(grid_original))

    with rasterio.open(PATH_DECLIVE) as src_declive, \
         rasterio.open(PATH_RASTER_USO_SOLO) as src_solo:

        nodata_declive = src_declive.nodata if src_declive.nodata is not None else -9999
        nodata_solo = src_solo.nodata if src_solo.nodata is not None else -9999

        for celula in tqdm(grid_original.itertuples(), total=len(grid_original)):
            
            geometria = celula.geometry
            id_atual = celula.id_ponto_int
            dados_coletados = {"id_ponto": id_atual}

            centroide_wgs = celula.centroide_wgs84
            dados_coletados["latitude_wgs84"] = centroide_wgs.y
            dados_coletados["longitude_wgs84"] = centroide_wgs.x

            valor_cache_vento = cache_nasa_vento.get(id_atual)
            valor_cache_solar = cache_nasa_solar.get(id_atual)
            
            if (valor_cache_vento is not None and pd.notna(valor_cache_vento) and valor_cache_vento > 0 and
                valor_cache_solar is not None and pd.notna(valor_cache_solar) and valor_cache_solar > 0):
                
                dados_coletados["vento_bruto_ms"] = valor_cache_vento
                dados_coletados["radiacao_solar_bruta"] = valor_cache_solar
            else:
                dados_nasa = obter_dados_nasa(centroide_wgs.y, centroide_wgs.x)
                
                dados_coletados["vento_bruto_ms"] = round(dados_nasa["vento"], 2)
                dados_coletados["radiacao_solar_bruta"] = round(dados_nasa["solar"], 2)
                
                time.sleep(0.5)

            stats_declive = rasterstats.zonal_stats(
                geometria, src_declive.read(1), affine=src_declive.transform,
                stats="mean", nodata=nodata_declive
            )
            valor_declive = stats_declive[0]['mean']
            dados_coletados["declive_bruto_graus"] = round(valor_declive, 2) if valor_declive is not None else 0.0

            stats_solo = rasterstats.zonal_stats(
                geometria, src_solo.read(1), affine=src_solo.transform,
                stats="majority", nodata=nodata_solo
            )
            valor_solo = stats_solo[0]['majority']
            dados_coletados["solo_bruto_codigo"] = int(valor_solo) if valor_solo is not None else 0

            resultado_conservacao = calcular_intersecao_conservacao(
                geometria, conservacao_otimizada, 'grupo'
            )
            dados_coletados["restricao_dados_json"] = json.dumps(resultado_conservacao)

            centroide_local = celula.centroide_local
            dist_urbana_m = centroide_local.distance(uniao_urbana)
            dist_rede_m = centroide_local.distance(uniao_subestacoes)
            dados_coletados["dist_urbana_bruto_km"] = round(dist_urbana_m / 1000, 2)
            dados_coletados["dist_rede_bruto_km"] = round(dist_rede_m / 1000, 2)

            dados_coletados["pct_intersecao_urbana"] = calcular_percentual_urbano(
                geometria, camadas["areas_urbanas"], geometria.area
            )

            lista_resultados.append(dados_coletados)

    if lista_resultados:
        df_final = pd.DataFrame(lista_resultados)
        df_final = df_final.sort_values(by='id_ponto')
