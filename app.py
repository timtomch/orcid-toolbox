import streamlit as st
import re
import pandas as pd
from src.orcid_data import fetch_orcid_data, format_timestamp
from src.references_matching import extract_and_process_references, prepare_orcid_works, match_references_to_orcid
import importlib.util
# TODO: Use gettext for localization
# The user locale is available at st.context.locale

st.set_page_config(page_title="Boîte à outils ORCID", page_icon=":toolbox:", layout="wide", initial_sidebar_state="expanded")

with st.sidebar:
    st.header(":toolbox: Boîte à outils ORCID")
    st.markdown('''
    Cette application réunit plusieurs outils pour interagir avec les données ORCID.
    ''')

    if "orcid_list" in st.session_state:
        st.button("Changer d'ORCID", type="secondary", on_click=lambda: st.session_state.pop("orcid_list"))

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

tab_works, tab_compare, tab_summary, tab_suggest = st.tabs(["Travaux", "Comparateur", "Résumé", "Suggestions"], default=default_tab)

# Check for ORCID from query params first and validate immediately
if "orcid_list" not in st.session_state:
    if st.query_params and "orcid" in st.query_params and st.query_params["orcid"]:
        # Parse from URL parameter
        orcid_from_url = st.query_params["orcid"]
        if isinstance(orcid_from_url, str):
            orcid_list = [orcid.strip() for orcid in orcid_from_url.split(',') if orcid.strip()]
        else:
            orcid_list = [str(orcid_from_url).strip()]
        
        # ORCID validation
        orcid_pattern = r'^[0-9a-zA-Z]{4}-[0-9a-zA-Z]{4}-[0-9a-zA-Z]{4}-[0-9a-zA-Z]{4}$'
        invalid_orcids = [orcid for orcid in orcid_list if not re.match(orcid_pattern, orcid)]
        
        if invalid_orcids:
            st.error(f"Format d'ORCID incorrect pour: {', '.join(invalid_orcids)}. Le format doit être XXXX-XXXX-XXXX-XXXX.")
            st.stop()
        
        # Store validated ORCID list from URL
        st.session_state.orcid_list = orcid_list
    else:
        # Show input field if no URL parameter
        orcid_input = st.text_input("Renseignez votre numéro ORCID (séparez plusieurs ORCIDs par des virgules):", key="orcid_input_field")
        
        # Validate on button click OR when input exists (Enter key pressed)
        if (st.button("Valider", type="primary") or orcid_input) and orcid_input:
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
            
            # ORCID validation before storing
            orcid_pattern = r'^[0-9a-zA-Z]{4}-[0-9a-zA-Z]{4}-[0-9a-zA-Z]{4}-[0-9a-zA-Z]{4}$'
            invalid_orcids = [orcid for orcid in orcid_list if not re.match(orcid_pattern, orcid)]
            
            if invalid_orcids:
                st.error(f"Format d'ORCID incorrect pour: {', '.join(invalid_orcids)}. Le format doit être XXXX-XXXX-XXXX-XXXX.")
                st.stop()
            
            # Store in session state once validated
            st.session_state.orcid_list = orcid_list
            st.rerun()
        
        st.stop()

# Retrieve from session state
orcid_list = st.session_state.orcid_list

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

            try:
                updated_person = raw.get('person', {}).get('last-modified-date', {}).get('value')
            except Exception:
                updated_person = None

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
                    format_timestamp(updated_person) if updated_person else "N/A",
                    summary_employments['last_modified'] if summary_employments else "N/A",
                    summary_educations['last_modified'] if summary_educations else "N/A",
                    summary_fundings['last_modified'] if summary_fundings else "N/A",
                    summary_works['last_modified'] if summary_works else "N/A"
                ]
            }
            
            st.table(updated_table, border="horizontal")

            st.subheader("Distribution des travaux par année de publication")

            st.bar_chart(df['publication-year'].value_counts().sort_index())

        with tab_compare:

            if len(orcid_list) > 1:
                st.warning("Le comparateur ne peut être utilisé qu'avec un seul ORCID à la fois. Veuillez fournir un seul ORCID.")
                st.stop()
            
            if importlib.util.find_spec("transformers") is None and importlib.util.find_spec("references_tractor") is None:
                st.warning("Cette fonctionalité nécessite la présence d'une bibliothèque pour l'extraction des références, telle que 'transformers' ou 'references_tractor'. Veuillez installer au moins l'une de ces bibliothèques.")
                st.stop()

            col_file, col_controls = st.columns(2)

            with col_file:

                refs_file = st.file_uploader("Téléchargez un fichier texte contenant des références bibliographiques à extraire :", type=["txt"])
                
                # Initialize variables
                matched_refs = []
                unmatched_refs = []
                
                if refs_file:
                    source_refs = refs_file.read().decode("utf-8")
                    
                    # Extract and process references
                    screened_refs, invalid_refs = extract_and_process_references(source_refs)

                    with st.sidebar:
                        st.success(f"{len(screened_refs)} références valides extraites, {len(invalid_refs)} références invalides ignorées.")

            with col_controls:
                
                if refs_file:
                    # Compare references with fuzzy matching
                    st.markdown("**Contrôle de correspondance :**")
                    
                    # Configure matching thresholds
                    confidence_interval = st.slider("Seuil de confiance (%)", 50, 100, (70, 95), 1)
                    
                    # Prepare ORCID works and match references
                    orcid_works = prepare_orcid_works(df)
                    matched_refs, unmatched_refs = match_references_to_orcid(screened_refs, orcid_works, confidence_interval[1])
                    
                    # Display statistics
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.metric("Références extraites", len(screened_refs))
                    with col_b:
                        st.metric("Trouvées dans ORCID", len(matched_refs))
                    with col_c:
                        st.metric("Manquantes dans ORCID", len(unmatched_refs))
                        

            if matched_refs:
                st.subheader(f"✅ {len(matched_refs)} références trouvées dans ORCID")
                sorting_option = st.segmented_control("Trier par :", ["Score", "Alpha", "Ordre"], key="sorting_option")
                for ref in matched_refs:
                    col_source, col_target = st.columns(2)
                    with col_source:
                        ref_number = ref['ref_number']
                        ref_ner = ref['ref_ner']
                        ref_title_display = ref_ner["TITLE"][0] if "TITLE" in ref_ner and ref_ner["TITLE"] else ref["text"][:50] + "..."
                        with st.expander(f"[{ref_number}] {ref_title_display}"):
                            st.caption("Texte original:")
                            st.write(ref.get('ref', {}).get('text', ''))
                            col_inner, col_outer = st.columns(2)
                            with col_inner:
                                if ref.get('ref_journal'):
                                    st.caption(f"Journal: {ref['ref_journal'] or 'N/A'}")
                                if ref.get('ref_year'):
                                    st.caption(f"Année: {ref['ref_year'] or 'N/A'}")
                                if ref.get('ref_doi'):
                                    st.caption(f"DOI: {ref['ref_doi'] or 'N/A'}")
                            with col_outer:
                                st.caption("Entités détectées :")
                                st.json(ref_ner, expanded=False)

                    with col_target:
                        confidence_color = "🟢" if ref['confidence'] >= 90 else "🟡" if ref['confidence'] >= 80 else "🟠"
                        with st.expander(f"{confidence_color} {ref['confidence']:.0f}% - {ref['orcid_title']}"):
                            st.caption(f"Score titre: {ref['title_score']}")
                            if ref.get('orcid_journal'):
                                st.caption(f"Journal: {ref['orcid_journal'] or 'N/A'} (score {ref['journal_score']})")
                            if ref.get('orcid_year'):
                                st.caption(f"Année: {ref['orcid_year'] or 'N/A'} (score {ref['year_score']})")
                            if ref.get('orcid_doi'):
                                st.caption(f"DOI: {ref['orcid_doi'] or 'N/A'} (score {ref['doi_score']})")
            
            if unmatched_refs:
                st.subheader(f"⚠️ Références à valider")

                # Sort by confidence descending
                unmatched_refs_sorted = sorted(unmatched_refs, key=lambda x: x['confidence'], reverse=True)

                for ref in unmatched_refs_sorted:
                    if confidence_interval[0] <= ref['confidence'] <= confidence_interval[1]:
                        col_source, col_target = st.columns(2)
                        with col_source:
                            ref_number = ref['ref_number']
                            ref_ner = ref['ref_ner']
                            ref_title_display = ref_ner["TITLE"][0] if "TITLE" in ref_ner and ref_ner["TITLE"] else ref["text"][:50] + "..."
                            with st.expander(f"[{ref_number}] {ref_title_display}"):
                                st.caption("Texte original:")
                                st.write(ref.get('ref', {}).get('text', ''))
                                col_inner, col_outer = st.columns(2)
                                with col_inner:
                                    if ref.get('ref_journal'):
                                        st.caption(f"Journal: {ref['ref_journal'] or 'N/A'}")
                                    if ref.get('ref_year'):
                                        st.caption(f"Année: {ref['ref_year'] or 'N/A'}")
                                    if ref.get('ref_doi'):
                                        st.caption(f"DOI: {ref['ref_doi'] or 'N/A'}")
                                with col_outer:
                                    st.caption("Entités détectées :")
                                    st.json(ref_ner, expanded=False)

                        with col_target:
                            confidence_color = "🟢" if ref['confidence'] >= 90 else "🟡" if ref['confidence'] >= 80 else "🟠"
                            with st.expander(f"{confidence_color} {ref['confidence']:.0f}% - {ref['orcid_title']}"):
                                st.caption(f"Score titre: {ref['title_score']}")
                                if ref.get('orcid_journal'):
                                    st.caption(f"Journal: {ref['orcid_journal'] or 'N/A'} (score {ref['journal_score']})")
                                if ref.get('orcid_year'):
                                    st.caption(f"Année: {ref['orcid_year'] or 'N/A'} (score {ref['year_score']})")
                                if ref.get('orcid_doi'):    
                                    st.caption(f"DOI: {ref['orcid_doi'] or 'N/A'} (score {ref['doi_score']})")
                
                st.subheader(f"❌ Références non trouvées")

                for ref in unmatched_refs_sorted:
                    if confidence_interval[0] > ref['confidence'] :
                        col_source, col_target = st.columns(2)
                        with col_source:
                            ref_number = ref['ref_number']
                            ref_ner = ref['ref_ner']
                            ref_title_display = ref_ner["TITLE"][0] if "TITLE" in ref_ner and ref_ner["TITLE"] else ref["text"][:50] + "..."
                            with st.expander(f"[{ref_number}] {ref_title_display}"):
                                st.write(ref.get('ref', {}).get('text', ''))
                                col_inner, col_outer = st.columns(2)
                                with col_inner:
                                    if ref.get('ref_journal'):
                                        st.caption(f"Journal: {ref['ref_journal'] or 'N/A'}")
                                    if ref.get('ref_year'):
                                        st.caption(f"Année: {ref['ref_year'] or 'N/A'}")
                                    if ref.get('ref_doi'):
                                        st.caption(f"DOI: {ref['ref_doi'] or 'N/A'}")
                                with col_outer:
                                    st.caption("Entités détectées :")
                                    st.json(ref_ner, expanded=False)
            


