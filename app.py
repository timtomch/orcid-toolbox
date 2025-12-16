import streamlit as st
import re
from src.orcid_data import fetch_orcid_data, format_timestamp

st.set_page_config(page_title="Boîte à outils ORCID", page_icon=":toolbox:", layout="wide", initial_sidebar_state="expanded")

with st.sidebar:
    st.header(":rotating_light: Expérimental!")
    st.markdown('''
    Cette application réunit plusieurs outils pour interagir avec les données ORCID.
    ''')

    st.header("Statut")


st.title(":toolbox: Boîte à outils ORCID")

if st.query_params and "tab" in st.query_params and st.query_params["tab"] in ["activites", "resume", "suggestions"]:
    match st.query_params["tab"]:
        case "activites":
            default_tab = "Autres activités"
        case "resume":
            default_tab = "Résumé"
        case "suggestions":
            default_tab = "Suggestions"
else:
    default_tab = None

tab_works, tab_activities, tab_summary, tab_suggest = st.tabs(["Travaux", "Autres activités", "Résumé", "Suggestions"], default=default_tab)

if st.query_params and "orcid" in st.query_params:
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
        df, raw = fetch_orcid_data(orcid_input)
        person_name = df['name'].iloc[0] if not df.empty and 'name' in df.columns else ''
        works_count = len(df)
    
    with tab_works:
        if works_count > 0:
            with st.sidebar:
                st.success(f"Données ORCID OK {orcid_input}")

            st.header(f"{works_count} travaux trouvés pour {person_name}")
            # Show a simple table of works
            try:
                st.dataframe(df)
            except Exception:
                st.write("Travaux disponibles")

    with tab_summary:
        st.header(f"Résumé du profil ORCID de {person_name} ({orcid_input})")

        st.link_button(f"Voir profil :material/open_in_new:", raw.get('orcid-identifier', {}).get('uri'))
    
        st.write(f"Créé le: {format_timestamp(raw.get('history', {}).get('submission-date', {}).get('value'))}")
        
        summary_works = {
            "count": works_count,
            "last_modified": format_timestamp(raw.get('activities-summary', {}).get('works', {}). get('last-modified-date', {}).get('value'),True)
            } if raw.get('activities-summary', {}).get('works', {}).get('last-modified-date') else None
        
        summary_employments = {
            "count": raw.get('activities-summary', {}).get('employments').get('affiliation-group', []).__len__(),
            "last_modified": format_timestamp(raw.get('activities-summary', {}).get('employments', {}). get('last-modified-date', {}).get('value'))
            } if raw.get('activities-summary', {}).get('employments', {}).get('last-modified-date') else None
        
        summary_educations = {
            "count": raw.get('activities-summary', {}).get('educations').get('affiliation-group', []).__len__(),
            "last_modified": format_timestamp(raw.get('activities-summary', {}).get('educations', {}). get('last-modified-date', {}).get('value'))
            } if raw.get('activities-summary', {}).get('educations', {}).get('last-modified-date') else None
        
        summary_fundings = {
            "count": raw.get('activities-summary', {}).get('fundings').get('affiliation-group', []).__len__(),
            "last_modified": format_timestamp(raw.get('activities-summary', {}).get('fundings', {}). get('last-modified-date', {}).get('value'),True)
            } if raw.get('activities-summary', {}).get('fundings', {}).get('last-modified-date') else None


        updated_table = {
            "Section": [
                ":material/person: Informations personnelles",
                ":material/work: Emploi",
                ":material/school: Formation et qualifications",
                ":material/money: Financements",
                ":material/docs: Travaux"
            ],
            "Complété": [
                "✅" if raw.get('person', {}).get('name') else "❌",
                f"✅ ({summary_employments['count']})" if summary_employments else "❌",
                f"✅ ({summary_educations['count']})" if summary_educations else "❌",
                f"✅ ({summary_fundings['count']})" if summary_fundings else "❌",
                f"✅ ({summary_works['count']})" if summary_works else "❌"
            ],
            "Dernière modification": [
                format_timestamp(raw.get('person', {}).get('last-modified-date', {}).get('value')),
                summary_employments['last_modified'] if summary_employments else "N/A",
                summary_educations['last_modified'] if summary_educations else "N/A",
                summary_fundings['last_modified'] if summary_fundings else "N/A",
                summary_works['last_modified'] if summary_works else "N/A"
            ]
        }
        
        st.table(updated_table, border="horizontal")


