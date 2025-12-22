import streamlit as st
import re
import pandas as pd
from src.orcid_data import fetch_orcid_data, format_timestamp
from references_tractor import ReferencesTractor
from references_tractor.utils.span import extract_references_and_mentions
from references_tractor.utils.prescreening import prescreen_references
from tqdm.notebook import tqdm  # type: ignore
from thefuzz import fuzz

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

# Debug: Check query params
# st.write("Query params:", dict(st.query_params))

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

        with tab_compare:

            if len(orcid_list) > 1:
                st.warning("Le comparateur ne peut être utilisé qu'avec un seul ORCID à la fois. Veuillez fournir un seul ORCID.")
                st.stop()

            col_source, col_target = st.columns(2)

            with col_source:
                st.subheader("Références à comparer")

                refs_file = st.file_uploader("Téléchargez un fichier texte contenant des références bibliographiques à extraire :", type=["txt"])
                if refs_file:
                    source_refs = refs_file.read().decode("utf-8")

                    # Initialize References Tractor for reference extraction
                    ref_tractor = ReferencesTractor()

                    st.markdown("**Références extraites :**")
                    extracted =  extract_references_and_mentions(source_refs, ref_tractor.span_pipeline)

                    references = extracted["references"]
                    mentions = extracted["mentions"]

                    screened_refs = prescreen_references(references, ref_tractor.prescreening_pipeline)
                    invalid_refs = [r for r in references if r not in screened_refs]

                    with st.sidebar:
                        st.success(f"{len(screened_refs)} références valides extraites, {len(invalid_refs)} références invalides ignorées.")

                    # Add reference numbers
                    for i, ref in enumerate(tqdm(screened_refs, desc="Linking References", unit=" reference"), start=1):
                        ref['ref_number'] = i
                        ref_text = ref["text"]

                        ref_ner = ref_tractor.process_ner_entities(ref_text)
                        ref['ner'] = ref_ner
                        ref_title_display = ref_ner["TITLE"][0] if "TITLE" in ref_ner and ref_ner["TITLE"] else ref_text[:50] + "..."
                        with st.expander(f"[{i}] {ref_title_display}"):
                            st.write(ref_ner)
                    

            with col_target:
                st.subheader(f"Références dans profil ORCID")
                
                if refs_file:
                    # Compare references with fuzzy matching
                    st.markdown("**Analyse de comparaison :**")
                    
                    # Configure matching thresholds
                    min_confidence = st.slider("Seuil de confiance minimum (%)", 70, 100, 90, 1)
                    
                    # Build ORCID works dataset for comparison
                    orcid_works = []
                    for idx, row in df.iterrows():
                        orcid_works.append({
                            'title': str(row['title']).lower().strip() if pd.notna(row['title']) else '',
                            'year': str(row['publication-year']).strip() if pd.notna(row['publication-year']) else '',
                            'journal': str(row['journal-title']).lower().strip() if pd.notna(row['journal-title']) else '',
                            'original_title': str(row['title']) if pd.notna(row['title']) else 'Sans titre'
                        })
                    
                    # Find matches using fuzzy matching with confidence scoring
                    matched_refs = []
                    unmatched_refs = []
                    
                    for ref in screened_refs:
                        ref_number = ref.get('ref_number', 0)
                        # Extract reference metadata
                        ref_title = ''
                        ref_orig_title = ''
                        ref_year = ''
                        ref_journal = ''
                        
                        if 'ner' in ref:
                            if 'TITLE' in ref['ner'] and ref['ner']['TITLE']:
                                ref_title = ref['ner']['TITLE'][0].lower().strip()
                                ref_orig_title = ref['ner']['TITLE'][0].strip()
                            if 'PUBLICATION_YEAR' in ref['ner'] and ref['ner']['PUBLICATION_YEAR']:
                                ref_year = ''.join(filter(str.isdigit, ref['ner']['PUBLICATION_YEAR'][0]))[:4]
                            if 'JOURNAL' in ref['ner'] and ref['ner']['JOURNAL']:
                                ref_journal = ref['ner']['JOURNAL'][0].lower().strip()
                        
                        if not ref_title:
                            continue
                        
                        # Find best match among ORCID works
                        best_match = None
                        best_confidence = 0
                        best_title_score = 0
                        best_year_score = 0
                        best_journal_score = 0
                        
                        for work in orcid_works:
                            if not work['title']:
                                continue
                            
                            # Calculate title similarity (70% weight)
                            title_score = fuzz.token_sort_ratio(ref_title, work['title'])
                            
                            # Calculate year match (15% weight)
                            year_score = 0
                            if ref_year and work['year']:
                                # Clean year strings and compare
                                try:
                                    ref_year_clean = str(int(float(ref_year)))
                                    work_year_clean = str(int(float(work['year'])))
                                    year_score = 100 if ref_year_clean == work_year_clean else 0
                                except (ValueError, TypeError) as e:
                                    year_score = 0
                            
                            # Calculate journal similarity (15% weight)
                            journal_score = 0
                            if ref_journal and work['journal']:
                                journal_score = fuzz.partial_ratio(ref_journal, work['journal'])
                            
                            # Weighted confidence score
                            confidence = (title_score * 0.7 + year_score * 0.15 + journal_score * 0.15)
                            
                            if confidence > best_confidence:
                                best_confidence = confidence
                                best_match = work
                                best_title_score = title_score
                                best_year_score = year_score
                                best_journal_score = journal_score
                        
                        # Store match if confidence exceeds threshold
                        if best_match and best_confidence >= min_confidence:
                            matched_refs.append({
                                'ref': ref,
                                'ref_number': ref_number,
                                'ref_title': ref_title,
                                'ref_orig_title': ref_orig_title,
                                'ref_year': ref_year,
                                'ref_journal': ref_journal,
                                'orcid_title': best_match['original_title'],
                                'orcid_year': best_match['year'],
                                'orcid_journal': best_match['journal'],
                                'confidence': best_confidence,
                                'title_score': best_title_score,
                                'year_score': best_year_score,
                                'journal_score': best_journal_score
                            })
                        else:
                            unmatched_refs.append({
                                'ref': ref,
                                'ref_number': ref_number,
                                'ref_title': ref_title,
                                'ref_orig_title': ref_orig_title,
                                'ref_year': ref_year,
                                'ref_journal': ref_journal,
                                'best_confidence': best_confidence if best_match else 0,
                                'title_score': title_score,
                                'year_score': year_score,
                                'journal_score': journal_score
                            })
                    
                    # Display statistics
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.metric("Références extraites", len(screened_refs))
                    with col_b:
                        st.metric("Trouvées dans ORCID", len(matched_refs), f"{len(matched_refs)/len(screened_refs)*100:.0f}%" if screened_refs else "0%")
                    with col_c:
                        st.metric("Manquantes dans ORCID", len(unmatched_refs))
                    
                    # Display matched references
                    if matched_refs:
                        # Sort by confidence descending
                        matched_refs_sorted = sorted(matched_refs, key=lambda x: x['confidence'], reverse=True)
                        with st.expander(f"✅ {len(matched_refs)} références trouvées dans ORCID", expanded=True):
                            for item in matched_refs_sorted:
                                confidence_color = "🟢" if item['confidence'] >= 90 else "🟡" if item['confidence'] >= 80 else "🟠"
                                st.markdown(f"{confidence_color} **[{item['ref_number']}]** {item['confidence']:.0f}% - {item['ref_orig_title']}")
                                st.caption(f"Titre dans ORCID: {item['orcid_title']} (score {item['title_score']})")
                                if item['ref_journal'] or item['orcid_journal']:
                                    st.caption(f"Journal: {item['ref_journal'] or 'N/A'} | ORCID: {item['orcid_journal'] or 'N/A'} (score {item['journal_score']})")
                                if item['ref_year'] or item['orcid_year']:
                                    st.caption(f"Année: {item['ref_year'] or 'N/A'} | ORCID: {item['orcid_year'] or 'N/A'} (score {item['year_score']})")
                                st.divider()
                    
                    # Display unmatched references
                    if unmatched_refs:
                        with st.expander(f"⚠️ {len(unmatched_refs)} références manquantes dans ORCID", expanded=True):
                            for item in unmatched_refs:
                                st.markdown(f"- **[{item['ref_number']}]** {item['ref_title']} ({item['ref_year'] or 'N/A'})")
                                if item['best_confidence'] > 0:
                                    st.caption(f"   Meilleure correspondance: {item['best_confidence']:.0f}% (sous le seuil)")
                                if item['ref_journal']:
                                    st.caption(f"   Journal: {item['ref_journal']}")



