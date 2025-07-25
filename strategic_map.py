import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import json
from pathlib import Path

# --- Page Configuration ---
st.set_page_config(
    page_title="Cloud Seeding Map",
    page_icon="🛰️",
    layout="wide"
)

# --- Title ---
st.title("Cloud Seeding")

# --- Data Loading ---
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DATA_PATH = SCRIPT_DIR / "cloud_seeding_data.json"
STATES_GEO_PATH = SCRIPT_DIR / "us_states.json"
DROUGHT_GEO_PATH = SCRIPT_DIR / "drought_data.json"

@st.cache_data
def load_data():
    project_data = json.load(open(PROJECT_DATA_PATH))
    states_geo = json.load(open(STATES_GEO_PATH))
    drought_geo_raw = json.load(open(DROUGHT_GEO_PATH))

    # Fix the non-standard drought GeoJSON
    if 'features' in drought_geo_raw:
        for feature in drought_geo_raw['features']:
            if 'properties' not in feature:
                properties = {k: v for k, v in feature.items() if k not in ['type', 'geometry']}
                feature['properties'] = properties
    
    return project_data, states_geo, drought_geo_raw

try:
    project_data_list, states_geo_data, drought_geo_data = load_data()
    df_projects = pd.DataFrame(project_data_list)
except FileNotFoundError as e:
    st.error(f"FATAL ERROR: A data file is missing. Please ensure all .json files are in the same folder. Missing file: {e.filename}")
    st.stop()

# --- Sidebar ---
st.sidebar.header("Map Layers")
st.sidebar.info("All map data is loaded from local files.")
show_regulatory_heatmap = st.sidebar.checkbox("Show Regulatory Heatmap", value=True)
show_drought_layer = st.sidebar.checkbox("Show Drought Data", value=True)

# --- Map Creation ---
m = folium.Map(location=[39.8283, -98.5795], zoom_start=4, tiles="CartoDB positron")

# --- Layer 1: Regulatory Heatmap ---
if show_regulatory_heatmap:
    reg_df = pd.DataFrame({
        'state': ['North Dakota', 'Utah', 'Colorado', 'Idaho', 'Nevada', 'Wyoming', 'Texas', 'California', 'Kansas', 'Montana'],
        'value': [1, 1, 1, 1, 1, 2, 2, 2, 2, 3]
    })
    folium.Choropleth(
        geo_data=states_geo_data, name='Regulatory Heatmap', data=reg_df,
        columns=['state', 'value'], key_on='feature.properties.name',
        fill_color='RdYlGn_r', fill_opacity=0.6, line_opacity=0.4,
        legend_name='Regulation level', nan_fill_color="gainsboro"
    ).add_to(m)

# --- Layer 2: Drought Data ---
if show_drought_layer:
    def style_function(feature):
        props = feature.get('properties', {})
        drought_level = int(props.get('DM', -1))
        return {'fillOpacity': 0.7, 'weight': 0.5, 'color': 'black',
                'fillColor': ('#730000' if drought_level == 4 else '#E60000' if drought_level == 3 else
                              '#FFAA00' if drought_level == 2 else '#FCD37F' if drought_level == 1 else
                              '#FFFF00' if drought_level == 0 else 'transparent')}
    folium.GeoJson(
        drought_geo_data, name='Drought Conditions', style_function=style_function,
        tooltip=folium.GeoJsonTooltip(fields=['DM'], aliases=['Drought Level (0-4):'])
    ).add_to(m)

# --- Layer 3: Project Markers (Cleaned) ---
for idx, row in df_projects.iterrows():
    icon_name = "plane" if "Aircraft" in row['delivery_method'] else "tower-broadcast"
    icon_color = "darkblue" if "Aircraft" in row['delivery_method'] else "cadetblue"
    
    # Simplified popup without logos
    popup_html = f"""
    <div style='width: 250px; font-family: sans-serif;'>
        <h4 style='margin-bottom:5px; font-size:14px;'>{row['program_name']}</h4>
        <p style='margin:0;'><b>Operator:</b> {row['operator']}</p>
        <a href="{row['source_url']}" target="_blank">Source Link</a>
    </div>
    """
    
    folium.Marker(
        location=[row['latitude'], row['longitude']],
        popup=folium.Popup(popup_html, max_width=280),
        tooltip=row['program_name'],
        icon=folium.Icon(color=icon_color, icon=icon_name, prefix='fa')
    ).add_to(m)

# --- Final Display ---
folium.LayerControl().add_to(m)
st_folium(m, width='100%', height=600)

st.markdown("---")
st.dataframe(df_projects)