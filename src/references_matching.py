# References matching module for comparing extracted references with ORCID works
# Uses fuzzy matching to find corresponding publications

import pandas as pd
from thefuzz import fuzz
from typing import List, Dict, Tuple, Any


def extract_and_process_references(text: str) -> Tuple[List[Dict], List[Dict]]:
    # Lazy imports to avoid loading nltk at module import time
    from references_tractor import ReferencesTractor
    from references_tractor.utils.span import extract_references_and_mentions
    from references_tractor.utils.prescreening import prescreen_references
    
    # Initialize References Tractor for reference extraction
    ref_tractor = ReferencesTractor()
    
    # Extract references and mentions
    extracted = extract_references_and_mentions(text, ref_tractor.span_pipeline)
    references = extracted["references"]
    mentions = extracted["mentions"]
    
    # Prescreen references
    screened_refs = prescreen_references(references, ref_tractor.prescreening_pipeline)
    invalid_refs = [r for r in references if r not in screened_refs]
    
    # Add reference numbers and process NER
    for i, ref in enumerate(screened_refs, start=1):
        ref['ref_number'] = i
        ref_text = ref["text"]
        ref_ner = ref_tractor.process_ner_entities(ref_text)
        ref['ner'] = ref_ner
    
    return screened_refs, invalid_refs


def prepare_orcid_works(df: pd.DataFrame) -> List[Dict[str, str]]:
    orcid_works = []
    for idx, row in df.iterrows():
        orcid_works.append({
            'title': str(row['title']).lower().strip() if pd.notna(row['title']) else '',
            'year': str(row['publication-year']).strip() if pd.notna(row['publication-year']) else '',
            'journal': str(row['journal-title']).lower().strip() if pd.notna(row['journal-title']) else '',
            'doi': str(row['doi']).strip() if pd.notna(row['doi']) else '',
            'original_title': str(row['title']) if pd.notna(row['title']) else 'Sans titre'
        })
    return orcid_works


def extract_reference_metadata(ref: Dict) -> Dict[str, str]:
    metadata = {
        'title': '',
        'orig_title': '',
        'year': '',
        'journal': '',
        'number': ref.get('ref_number', 0),
        'doi': '',
        'ner': ''
    }
    
    if 'ner' not in ref:
        return metadata
    
    ner = ref['ner']
    metadata['ner'] = ner
    
    # Extract title
    if 'TITLE' in ner and ner['TITLE']:
        metadata['title'] = ner['TITLE'][0].lower().strip()
        metadata['orig_title'] = ner['TITLE'][0].strip()
    
    # Extract year
    if 'PUBLICATION_YEAR' in ner and ner['PUBLICATION_YEAR']:
        metadata['year'] = ''.join(filter(str.isdigit, ner['PUBLICATION_YEAR'][0]))[:4]
    
    # Extract journal
    if 'JOURNAL' in ner and ner['JOURNAL']:
        metadata['journal'] = ner['JOURNAL'][0].lower().strip()
    
    # Extract DOI
    if 'DOI' in ner and ner['DOI']:
        metadata['doi'] = ner['DOI'][0].strip()
    
    return metadata


def calculate_match_score(ref_metadata: Dict[str, str], work: Dict[str, str]) -> Tuple[float, Dict[str, float]]:
    scores = {
        'title': 0,
        'year': 0,
        'journal': 0,
        'doi': 0
    }
    
    # Calculate title similarity (50% weight)
    if ref_metadata['title'] and work['title']:
        scores['title'] = fuzz.token_sort_ratio(ref_metadata['title'], work['title'])
    
    # Calculate year match (10% weight)
    if ref_metadata['year'] and work['year']:
        try:
            ref_year_clean = str(int(float(ref_metadata['year'])))
            work_year_clean = str(int(float(work['year'])))
            scores['year'] = 100 if ref_year_clean == work_year_clean else 0
        except (ValueError, TypeError):
            scores['year'] = 0
    
    # Calculate journal similarity (10% weight)
    if ref_metadata['journal'] and work['journal']:
        scores['journal'] = fuzz.partial_ratio(ref_metadata['journal'], work['journal'])

    # Calculate DOI match (high weight when present)
    if ref_metadata['doi'] and work['doi']:
        scores['doi'] = 100 if ref_metadata['doi'].lower() == work['doi'].lower() else 0
    
    # Dynamic weighted confidence score
    # When DOI is present, it gets 40% weight; otherwise distribute to other fields
    if ref_metadata['doi'] and work['doi']:
        confidence = (scores['title'] * 0.4 + scores['year'] * 0.1 + scores['journal'] * 0.1 + scores['doi'] * 0.4)
    else:
        confidence = (scores['title'] * 0.6 + scores['year'] * 0.2 + scores['journal'] * 0.2)
    
    return confidence, scores


def match_references_to_orcid(
    screened_refs: List[Dict],
    orcid_works: List[Dict],
    min_confidence: float = 70.0
) -> Tuple[List[Dict], List[Dict]]:
    matched_refs = []
    unmatched_refs = []
    
    for ref in screened_refs:
        ref_metadata = extract_reference_metadata(ref)
        
        if not ref_metadata['title']:
            continue
        
        # Find best match among ORCID works
        best_match = None
        best_confidence = 0
        best_scores = {'title': 0, 'year': 0, 'journal': 0, 'doi': 0}
        
        for work in orcid_works:
            if not work['title']:
                continue
            
            confidence, scores = calculate_match_score(ref_metadata, work)
            
            if confidence > best_confidence:
                best_confidence = confidence
                best_match = work
                best_scores = scores
        
        # Store match if confidence exceeds threshold
        if best_match and best_confidence >= min_confidence:
            matched_refs.append({
                'ref': ref,
                'ref_ner': ref_metadata['ner'],
                'ref_number': ref_metadata['number'],
                'ref_title': ref_metadata['title'],
                'ref_orig_title': ref_metadata['orig_title'],
                'ref_year': ref_metadata['year'],
                'ref_journal': ref_metadata['journal'],
                'ref_doi': ref_metadata['doi'],
                'orcid_title': best_match['original_title'],
                'orcid_year': best_match['year'],
                'orcid_journal': best_match['journal'],
                'orcid_doi': best_match['doi'],
                'confidence': best_confidence,
                'title_score': best_scores['title'],
                'year_score': best_scores['year'],
                'journal_score': best_scores['journal'],
                'doi_score': best_scores['doi']
            })
        else:
            unmatched_refs.append({
                'ref': ref,
                'ref_ner': ref_metadata['ner'],
                'ref_number': ref_metadata['number'],
                'ref_title': ref_metadata['title'],
                'ref_orig_title': ref_metadata['orig_title'],
                'ref_year': ref_metadata['year'],
                'ref_journal': ref_metadata['journal'],
                'ref_doi': ref_metadata['doi'],
                'orcid_title': best_match['original_title'] if best_match else '',
                'orcid_year': best_match['year'] if best_match else '',
                'orcid_journal': best_match['journal'] if best_match else '',
                'orcid_doi': best_match['doi'] if best_match else '',
                'confidence': best_confidence if best_match else 0,
                'title_score': best_scores['title'],
                'year_score': best_scores['year'],
                'journal_score': best_scores['journal'],
                'doi_score': best_scores['doi']
            })
    
    return matched_refs, unmatched_refs
