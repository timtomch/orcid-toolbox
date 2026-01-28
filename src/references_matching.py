# References matching module for comparing extracted references with ORCID works
# Uses fuzzy matching to find corresponding publications

import pandas as pd
import re
from thefuzz import fuzz
from typing import List, Dict, Tuple, Any
import importlib.util

# Extract individual references from large text block
def extract_references_from_text(text: str) -> List[Dict]:
    references = []
    
    # Common patterns: [1], (1), 1., etc. at start of line
    lines = text.split('\n')
    current_ref = []
    ref_number = 0
    
    for line in lines:
        stripped_line = line.strip()
        
        # Blank line separates references
        if not stripped_line:
            if current_ref:
                # Save current reference
                ref_text = ' '.join(current_ref)
                ref_number += 1
                references.append({
                    'text': ref_text,
                    'ref_number': ref_number,
                    'start': 0,
                    'end': len(ref_text)
                })
                current_ref = []
            continue
            
        # Check if line starts with a reference number
        match = re.match(r'^[\[\(]?(\d+)[\]\)\.]\s*(.+)', stripped_line)
        if match:
            # Save previous reference if exists
            if current_ref:
                ref_text = ' '.join(current_ref)
                references.append({
                    'text': ref_text,
                    'ref_number': ref_number,
                    'start': 0,
                    'end': len(ref_text)
                })
            # Start new reference
            ref_number = int(match.group(1))
            current_ref = [match.group(2)]
        elif current_ref:
            # Continue current reference
            current_ref.append(stripped_line)
        else:
            # Start a new reference without numbering
            ref_number += 1
            current_ref = [stripped_line]
    
    # Add last reference
    if current_ref:
        ref_text = ' '.join(current_ref)
        references.append({
            'text': ref_text,
            'ref_number': ref_number,
            'start': 0,
            'end': len(ref_text)
        })
    
    return references

# Run individual references through NER model and process entities
# Inspired by https://github.com/sirisacademic/references-tractor
def extract_ner_entities(text: str) -> Dict[str, List[str]]:
    # Lazy imports to avoid loading models before they are needed
    from transformers import pipeline

    # Load the citation parser model from SIRIS lab
    citation_parser = pipeline("ner", model="SIRIS-Lab/citation-parser-ENTITY", aggregation_strategy="simple")

    try:
        # Run NER pipeline
        raw_results = citation_parser(text)

        # Init result structure
        entities = {
            'TITLE': [],
            'AUTHORS': [],
            'VOLUME': [],
            'ISSUE': [],
            'PUBLICATION_YEAR': [],
            'DOI': [],
            'ISSN': [],
            'ISBN': [],
            'PAGE_FIRST': [],
            'PAGE_LAST': [],
            'JOURNAL': [],
            'EDITOR': []
        }

        # STEP 1 — sort entities by start index
        raw_results = sorted(raw_results, key=lambda x: x["start"])

        merged = []
        current = None

        def flush():
            nonlocal current, merged
            if current:
                merged.append(current)
                current = None

        for ent in raw_results:
            group = ent["entity_group"]
            word = ent["word"]
            start = ent["start"]
            end = ent["end"]

            if current is None:
                current = {
                    "entity_group": group,
                    "word": word,
                    "start": start,
                    "end": end,
                    "score": ent["score"]
                }
                continue

            # Check if mergeable:
            same_group = (group == current["entity_group"])
            touching = (start <= current["end"] + 1)

            if same_group and touching and not group in ["VOLUME", "ISSUE"]:
                # merge text
                current["word"] += word
                current["end"] = end
                current["score"] = max(current["score"], ent["score"])
            else:
                flush()
                current = {
                    "entity_group": group,
                    "word": word,
                    "start": start,
                    "end": end,
                    "score": ent["score"]
                }

        flush()

        # STEP 2 — convert into dict and populate entities
        for ent in merged:
            label = ent["entity_group"]
            entity_text = ent["word"].strip()
            if label in entities:
                entities[label].append(entity_text)
        
        # STEP 3 — clean up special cases
        # Merge DOI fragments and extract just the DOI identifier
        if 'DOI' in entities and entities['DOI']:
            if len(entities['DOI']) > 1:
                # Join all DOI parts
                merged_doi = ''.join(entities['DOI'])
            else:
                merged_doi = entities['DOI'][0]
            
            # Extract just the DOI identifier (e.g., 10.1037/cbs0000411)
            # Remove URL prefixes and clean up
            merged_doi = merged_doi.lstrip('.')
            # Remove common URL prefixes
            merged_doi = re.sub(r'^.*?://doi\.org/', '', merged_doi)
            merged_doi = re.sub(r'^.*?://dx\.doi\.org/', '', merged_doi)
            merged_doi = re.sub(r'^doi\.org/', '', merged_doi)
            merged_doi = re.sub(r'^dx\.doi\.org/', '', merged_doi)
            
            # Keep only if it matches DOI pattern (10.xxxxx/...)
            if merged_doi and re.match(r'10\.\d+/', merged_doi):
                entities['DOI'] = [merged_doi]
            else:
                entities['DOI'] = []
        
        # Split VOLUME and ISSUE if both are detected together
        if 'VOLUME' in entities and len(entities['VOLUME']) == 2:
            entities['ISSUE'] = [entities['VOLUME'][1]]
            entities['VOLUME'] = [entities['VOLUME'][0]]
        
        # Remove hyphens from page numbers
        if 'PAGE_FIRST' in entities and entities['PAGE_FIRST']:
            entities['PAGE_FIRST'] = [p.strip('-') for p in entities['PAGE_FIRST']]
        if 'PAGE_LAST' in entities and entities['PAGE_LAST']:
            entities['PAGE_LAST'] = [p.strip('-') for p in entities['PAGE_LAST']]

        return entities
    
    except Exception as e:
        print(f"Error during NER extraction: {e}")
        return {}


# Main function to extract and process references
def extract_transformer(text: str, progress_callback=None) -> Tuple[List[Dict], List[Dict]]:

    screened_refs = extract_references_from_text(text)
    invalid_refs = []
    total_refs = len(screened_refs)

    for i, ref in enumerate(screened_refs):
        ref['ref_number'] = i
        ref_text = ref["text"]
        ref_ner = extract_ner_entities(ref_text)
        ref['ner'] = ref_ner
        
        # Report progress if callback is provided
        if progress_callback:
            progress_callback(i + 1, total_refs)
    
    return screened_refs, invalid_refs


def extract_references_tractor(text: str, progress_callback=None) -> Tuple[List[Dict], List[Dict]]:
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
    
    total_refs = len(screened_refs)
    # Add reference numbers and process NER
    for i, ref in enumerate(screened_refs, start=1):
        ref['ref_number'] = i
        ref_text = ref["text"]
        ref_ner = ref_tractor.process_ner_entities(ref_text)
        ref['ner'] = ref_ner
        
        # Report progress if callback is provided
        if progress_callback:
            progress_callback(i, total_refs)
    
    return screened_refs, invalid_refs

# If references-tractor package is available locally, use it; otherwise, fall back to transformer-based extraction
def extract_and_process_references(text: str, progress_callback=None) -> Tuple[List[Dict], List[Dict]]:
    if importlib.util.find_spec("references_tractor"):
        return extract_references_tractor(text, progress_callback)
    elif importlib.util.find_spec("transformers"):
        return extract_transformer(text, progress_callback)
    else:
        raise ImportError("Erreur, une des bibliothèques nécessaires n'est pas installée. Veuillez installer 'references-tractor' ou 'transformers'.")


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
            scores['year'] = 100 if ref_metadata['year'].strip() == work['year'].strip() else 0
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
