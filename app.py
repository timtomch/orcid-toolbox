import streamlit as st
import streamlit.components.v1 as components
import re
from src.orcid_data import fetch_orcid_data

st.set_page_config(page_title="Boîte à outils ORCID", page_icon=":toolbox:", layout="wide", initial_sidebar_state="expanded")

with st.sidebar:
    st.header(":rotating_light: Expérimental!")
    st.markdown('''
    Plus d'informations à venir.
    ''')


st.title(":toolbox: Boîte à outils ORCID")

if st.query_params:
    orcid_input = st.query_params["orcid"]
else:
    orcid_input = st.text_input("Renseignez votre numéro ORCID:")

if orcid_input:
    # ORCID validation
    orcid_pattern = r'^[0-9a-zA-Z]{4}-[0-9a-zA-Z]{4}-[0-9a-zA-Z]{4}-[0-9a-zA-Z]{4}$'
    if not re.match(orcid_pattern, orcid_input):
        st.error("Format d'ORCID incorrect. Le format doit être XXXX-XXXX-XXXX-XXXX.")
        st.stop()

    with st.spinner('Chargement...'):
        data = fetch_orcid_data(orcid_input)
    
    if data.get("count", 0) > 0 and data.get("publications"):
        st.success(f"Données récupérées pour ORCID {orcid_input}:")

        st.header(f"{data['count']} travaux trouvés pour {data['name']}:")

        for index, row in enumerate(data['publications'], start=1):
            # A container for each publications
            with st.container(border=True):

                col1, col2 = st.columns([3, 1])

                col1.subheader(f"{index}. {row['title']}")
                if row.get("doi"):
                    with col2:
                        components.html(f'<div style="height:100px; display: flex; align-items:center; justify-content: flex-end;"><span class="__dimensions_badge_embed__" data-doi="{row['doi']}" data-legend="hover-left" data-style="small_circle"></span></div><script async src="https://badge.dimensions.ai/badge.js" charset="utf-8"></script>')