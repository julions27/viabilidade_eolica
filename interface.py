import streamlit as st
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium
import branca

st.set_page_config(layout="wide")
st.title("Viabilidade de Usinas Eólicas - RN")

df = pd.read_csv("resultados/resultados_finais_viabilidade_zonal.csv", sep=";")

for col in ['latitude_wgs84', 'longitude_wgs84', 'indice_final']:
    df[col] = df[col].astype(str).str.replace(',', '.').astype(float)

df_aprovados = df[(df['motivo_veto'].str.lower() == "aprovado")]

gdf_csv = gpd.GeoDataFrame(
    df_aprovados,
    geometry=gpd.points_from_xy(df_aprovados.longitude_wgs84, df_aprovados.latitude_wgs84)
)
gdf_csv.set_crs("EPSG:4326", inplace=True)

gdf_rn = gpd.read_file("dados/rn.shp").to_crs("EPSG:4326")
bounds = gdf_rn.total_bounds
centro_lat = (bounds[1] + bounds[3]) / 2
centro_lon = (bounds[0] + bounds[2]) / 2

def buscar_melhores(lat, lon, gdf, n=5, raio_metros=10000):
    gdf_m = gdf.to_crs(epsg=31983)

    clique = gpd.GeoSeries([Point(lon, lat)], crs="EPSG:4326").to_crs(epsg=31983)[0]

    gdf_m['distancia'] = gdf_m.geometry.distance(clique)

    gdf_filtrados = gdf_m[gdf_m['distancia'] <= raio_metros]

    if len(gdf_filtrados) < n:
        return gdf_filtrados.sort_values("indice_final", ascending=False)

    return gdf_filtrados.sort_values("indice_final", ascending=False).head(n)

def cor_indice(indice):
    if indice >= 8:
        return 'green'
    elif indice >= 6:
        return 'blue'
    else:
        return 'red'

st.sidebar.header("Filtros")
indice_min = st.sidebar.slider(
    "Índice mínimo para busca",
    float(gdf_csv['indice_final'].min()),
    float(gdf_csv['indice_final'].max()),
    float(gdf_csv['indice_final'].min())
)
gdf_filtrado = gdf_csv[gdf_csv['indice_final'] >= indice_min]

if 'ultimo_clique' not in st.session_state:
    st.session_state.ultimo_clique = None

st.write("Clique no mapa para buscar os melhores locais próximos para instalar uma usina eólica:")

m = folium.Map(location=[centro_lat, centro_lon], zoom_start=8, tiles="CartoDB positron")
folium.GeoJson(
    gdf_rn,
    style_function=lambda feature: {
        "fillColor": "blue",
        "color": "black",
        "weight": 2,
        "fillOpacity": 0.3
    }
).add_to(m)

map_data = st_folium(m, width=700, height=600, key="mapa_inicial")

if map_data["last_clicked"] is not None:
    st.session_state.ultimo_clique = (
        map_data["last_clicked"]["lat"],
        map_data["last_clicked"]["lng"]
    )

col1, col2 = st.columns([2, 1])

with col1:
    if st.session_state.ultimo_clique is not None:
        lat, lon = st.session_state.ultimo_clique
        zoom = 12

        legenda_mapa = """
        {% macro html(this, kwargs) %}
        <div style="
            position: fixed;
            bottom: 20px;
            left: 10px;
            padding: 12px;
            font-size: 14px;
            background-color: white;
            z-index: 9999;
            opacity: 0.7;
            border: 2px solid grey;
            border-radius: 5px;
            color: black !important;
        ">
            <p style="margin: 0 0 6px 0;"><b>Legenda</b></p>
            <p style="margin: 4px 0;">
                <span style="color:green; font-size:16px;">&#9673;</span>
                <span style="white-space: nowrap;"> Ótimo 𐤟 Índice ≥ 8</span>
            </p>
            <p style="margin: 4px 0;">
                <span style="color:blue; font-size:16px;">&#9673;</span>
                <span style="white-space: nowrap;"> Intermediário 𐤟 6 ≤ Índice < 8</span>
            </p>
            <p style="margin: 4px 0;">
                <span style="color:red; font-size:16px;">&#9673;</span>
                <span style="white-space: nowrap;"> Ruim 𐤟 Índice < 6</span>
            </p>
        </div>
        {% endmacro %}
        """

        legenda = branca.element.MacroElement()
        legenda._template = branca.element.Template(legenda_mapa)

        m2 = folium.Map(location=[lat, lon], zoom_start=zoom, tiles="CartoDB positron", key="mapa_atualizado")
        folium.GeoJson(
            gdf_rn,
            style_function=lambda feature: {
                "fillColor": "yellow",
                "color": "black",
                "weight": 2,
                "fillOpacity": 0.3
            }
        ).add_to(m2)
        m2.add_child(legenda)

        folium.Marker(
            location=[lat, lon],
            popup="Local clicado",
            icon=folium.Icon(color="red", icon="info-sign")
        ).add_to(m2)

        resultados = buscar_melhores(lat, lon, gdf_filtrado, n=5, raio_metros=10000).to_crs(epsg=4326)
        resultados = resultados.sort_values(by='indice_final', ascending=False).reset_index(drop=True)

        heat_data = []
        posicoes = ["Melhor localização", "Segunda melhor localização", "Terceira melhor localização",
                    "Quarta melhor localização", "Quinta melhor localização"]

        for i, row in enumerate(resultados.itertuples()):
            intensity = row.indice_final * (3 if i == 0 else 1)
            heat_data.append([row.geometry.y, row.geometry.x, intensity])

            for dy in [-0.01, 0, 0.01]:
                for dx in [-0.01, 0, 0.01]:
                    if dy == 0 and dx == 0:
                        continue
                    heat_data.append([row.geometry.y + dy, row.geometry.x + dx, intensity * 0.5])

            tooltip_text = f"{posicoes[i]} (ID: {row.id_ponto})"
            folium.CircleMarker(
                location=[row.geometry.y, row.geometry.x],
                radius=7,
                color=cor_indice(row.indice_final),
                fill=True,
                fill_opacity=0.8,
                tooltip=tooltip_text
            ).add_to(m2)

        HeatMap(
            heat_data,
            radius=35,
            blur=40,
            min_opacity=0.3,
            max_zoom=12
        ).add_to(m2)

        st_folium(m2, width=700, height=600)

with col2:
    st.subheader("Melhores pontos próximos")

    if st.session_state.ultimo_clique is None:
        st.write("Clique em qualquer lugar do mapa para visualizar os pontos mais próximos.")
    else:
        if resultados.empty:
            st.warning("Não há nenhum localização adequada para instalação de usinas no raio de 10 km a partir do ponto clicado.")
        else:
            resultados_todos_display = resultados.copy()
            resultados_todos_display["latitude"] = resultados_todos_display.geometry.y
            resultados_todos_display["longitude"] = resultados_todos_display.geometry.x

            resultados_todos_display = resultados_todos_display[
                ["id_ponto", "indice_final", "distancia", "latitude", "longitude"]
            ].rename(columns={
                "id_ponto": "ID",
                "indice_final": "Índice Final",
                "distancia": "Distância (m)",
                "latitude": "Latitude",
                "longitude": "Longitude"
            })

            resultados_todos_display["Índice Final"] = resultados_todos_display["Índice Final"].round(2)
            resultados_todos_display["Distância (m)"] = resultados_todos_display["Distância (m)"].round(2)
            resultados_todos_display["Latitude"] = resultados_todos_display["Latitude"].round(6)
            resultados_todos_display["Longitude"] = resultados_todos_display["Longitude"].round(6)

            resultados_todos_display = resultados_todos_display.sort_values(by="Índice Final", ascending=False)
            resultados_todos_display = resultados_todos_display.reset_index(drop=True)

            posicoes = [f"{i+1}º" for i in range(len(resultados_todos_display))]
            resultados_todos_display.index = posicoes

            st.dataframe(resultados_todos_display, width='stretch')