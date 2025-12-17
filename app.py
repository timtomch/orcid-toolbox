import streamlit as st
import re
from src.orcid_data import fetch_orcid_data, format_timestamp

st.set_page_config(page_title="Boîte à outils ORCID", page_icon=":toolbox:", layout="wide", initial_sidebar_state="expanded")

with st.sidebar:
    st.header(":toolbox: Boîte à outils ORCID")
    st.markdown('''
    Cette application réunit plusieurs outils pour interagir avec les données ORCID.
    ''')

    st.header("Statut")


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

# Debug: Check query params
# st.write("Query params:", dict(st.query_params))

orcid_input = None
if st.query_params and "orcid" in st.query_params and st.query_params["orcid"]:
    orcid_input = st.query_params["orcid"]
elif "orcid_input_field" in st.session_state and st.session_state.orcid_input_field:
    # Use the value from session state without showing the input again
    orcid_input = st.session_state.orcid_input_field
else:
    # Only show input if we don't have an ORCID yet
    orcid_input = st.text_input("Renseignez votre numéro ORCID (séparez plusieurs ORCIDs par des virgules):", key="orcid_input_field")

if orcid_input:
    # Parse and normalize orcid_input to always be a list
    if isinstance(orcid_input, str):
        orcid_list = [orcid.strip() for orcid in orcid_input.split(',') if orcid.strip()]
    elif isinstance(orcid_input, list):
        orcid_list = [orcid.strip() for orcid in orcid_input if orcid.strip()]
    else:
        orcid_list = [str(orcid_input).strip()]
    
    if not orcid_list:
        st.error("Veuillez fournir au moins un ORCID valide.")
        st.stop()

if 'orcid_list' in locals() and orcid_list is not None:
    # ORCID validation
    orcid_pattern = r'^[0-9a-zA-Z]{4}-[0-9a-zA-Z]{4}-[0-9a-zA-Z]{4}-[0-9a-zA-Z]{4}$'
    invalid_orcids = [orcid for orcid in orcid_list if not re.match(orcid_pattern, orcid)]
    
    if invalid_orcids:
        st.error(f"Format d'ORCID incorrect pour: {', '.join(invalid_orcids)}. Le format doit être XXXX-XXXX-XXXX-XXXX.")
        st.stop()
    
    # Process each ORCID
    for idx, orcid_input in enumerate(orcid_list):     
        with st.spinner(f'Chargement de {orcid_input}...'):
            df, raw = fetch_orcid_data(orcid_input)
            person_name = df['name'].iloc[0] if not df.empty and 'name' in df.columns else ''
            works_count = len(df)
        
        with tab_works:
            if works_count > 0:
                with st.sidebar:
                    st.success(f"Données ORCID OK {orcid_input}")

                col1, col2 = st.columns([4,1],vertical_alignment="bottom")
                with col1:
                    st.header(f"{works_count} travaux trouvés pour {person_name}")
                with col2:
                    st.link_button(f"Voir profil {orcid_input} :material/open_in_new:", raw.get('orcid-identifier', {}).get('uri'))     

                # Add an option to filter by type
                if 'type' in df.columns:
                    types = sorted(df['type'].dropna().unique().tolist())
                    selected_types = st.multiselect(
                        "Filtrer par type:",
                        types,
                        placeholder="Sélectionnez les types de travaux à afficher"
                        )
                    if selected_types:
                        filtered_df = df[df['type'].isin(selected_types)]
                    else:
                        filtered_df = df
                else:
                    filtered_df = df
                
                # Show a simple table of works
                try:
                    st.dataframe(filtered_df,
                                 column_config={
                                     "put-code": None,
                                     "modified-date": None,
                                     "modified-by": None,
                                     "title": "Titre",
                                     "type": "Type",
                                     "journal-title": "Titre de revue",
                                     "publication-year": "Année",
                                     "external-ids": None,
                                     "visibility": None,
                                     "doi": "DOI",
                                     "url": st.column_config.LinkColumn("Lien", display_text=":material/open_in_new:"),
                                     "orcid": None,
                                     "name": None
                                     },
                                     column_order=["title", "journal-title", "publication-year", "type", "doi", "url"], 
                                 height="content", 
                                 hide_index=True)
                except Exception:
                    st.write("Aucun travail disponible à afficher.")

        with tab_summary:

            col1, col2 = st.columns([4,1],vertical_alignment="bottom")
            with col1:
                st.header(f"Résumé du profil ORCID de {person_name}")
            with col2:
                st.link_button(f"Voir profil {orcid_input} :material/open_in_new:", raw.get('orcid-identifier', {}).get('uri'))
        
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


