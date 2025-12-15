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
        data = fetch_orcid_data(orcid_input)
    
    with tab_works:
        if data.get("count", 0) > 0 and data.get("publications"):
            with st.sidebar:
                st.success(f"Données ORCID OK {orcid_input}")

            st.header(f"{data['count']} travaux trouvés pour {data['name']}")

            for index, row in enumerate(data['publications'], start=1):
                # A container for each publications
                with st.container(border=True):
                    st.subheader(f"{index}. {row['title']}")
                    if row.get('doi'):
                        st.link_button(f"DOI: {row['doi']}", "https://doi.org/"+row['doi'])
                    
                    st.write(f"Type: {row.get('type', 'N/A')}")
                    st.write(f"Dernière mise à jour: {row.get('modified-date')} par {row.get('modified-by', 'N/A')}")

    with tab_summary:
        st.header(f"Résumé du profil ORCID de {data['name']} ({orcid_input})")

        st.link_button(f"Voir profil :material/open_in_new:", data['raw'].get('orcid-identifier', {}).get('uri'))
    
        st.write(f"Créé le: {format_timestamp(data['raw'].get('history', {}).get('submission-date', {}).get('value'))}")
        
        summary_works = {
            "count": data['count'],
            "last_modified": format_timestamp(data['raw'].get('activities-summary', {}).get('works', {}). get('last-modified-date', {}).get('value'),True)
            } if data['raw'].get('activities-summary', {}).get('works', {}).get('last-modified-date') else None
        
        summary_employments = {
            "count": data['raw'].get('activities-summary', {}).get('employments').get('affiliation-group', []).__len__(),
            "last_modified": format_timestamp(data['raw'].get('activities-summary', {}).get('employments', {}). get('last-modified-date', {}).get('value'))
            } if data['raw'].get('activities-summary', {}).get('employments', {}).get('last-modified-date') else None
        
        summary_educations = {
            "count": data['raw'].get('activities-summary', {}).get('educations').get('affiliation-group', []).__len__(),
            "last_modified": format_timestamp(data['raw'].get('activities-summary', {}).get('educations', {}). get('last-modified-date', {}).get('value'))
            } if data['raw'].get('activities-summary', {}).get('educations', {}).get('last-modified-date') else None
        
        summary_fundings = {
            "count": data['raw'].get('activities-summary', {}).get('fundings').get('affiliation-group', []).__len__(),
            "last_modified": format_timestamp(data['raw'].get('activities-summary', {}).get('fundings', {}). get('last-modified-date', {}).get('value'),True)
            } if data['raw'].get('activities-summary', {}).get('fundings', {}).get('last-modified-date') else None


        updated_table = {
            "Section": [
                ":material/person: Informations personnelles",
                ":material/work: Emploi",
                ":material/school: Formation et qualifications",
                ":material/money: Financements",
                ":material/docs: Travaux"
            ],
            "Complété": [
                "✅" if data['raw'].get('person', {}).get('name') else "❌",
                f"✅ ({summary_employments['count']})" if summary_employments else "❌",
                f"✅ ({summary_educations['count']})" if summary_educations else "❌",
                f"✅ ({summary_fundings['count']})" if summary_fundings else "❌",
                f"✅ ({summary_works['count']})" if summary_works else "❌"
            ],
            "Dernière modification": [
                format_timestamp(data['raw'].get('person', {}).get('last-modified-date', {}).get('value')),
                summary_employments['last_modified'] if summary_employments else "N/A",
                summary_educations['last_modified'] if summary_educations else "N/A",
                summary_fundings['last_modified'] if summary_fundings else "N/A",
                summary_works['last_modified'] if summary_works else "N/A"
            ]
        }
        
        st.table(updated_table, border="horizontal")


