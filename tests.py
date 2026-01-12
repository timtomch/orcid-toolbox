from src.orcid_data import fetch_orcid_data
from src.references_matching import extract_and_process_references

df, raw_data = fetch_orcid_data("0000-0002-5210-7083")
name = df['name'].iloc[0] if not df.empty and 'name' in df.columns else ''
print(f"Name : {name}")
print(f"Total publications: {len(df)}")
for _, row in df.iterrows():
    title = row.get('title') if 'title' in row else None
    doi = row.get('doi') if 'doi' in row else None
    print(f"- {title} (DOI: {doi or 'N/A'})")

text = """
1. Lépine, M; Brassard, G; Bélanger, A; Dumouchel, M. (2025). Agir en tant que « passeur culturel »… en
commençant par soi!. Vivre le primaire. 38(2): 86-87.

Grady, J. S., Her, M., Moreno, G., Perez, C., & Yelinek, J. (2019). Emotions in storybooks: A comparison of storybooks that represent ethnic and racial groups in the United States. Psychology of Popular Media Culture, 8(3), 207–217. https://doi.org/10.1037/ppm0000185

Pope, J. P., & Wall, H. (2025). Is the goal intrinsic or extrinsic? Examining self-determination theory researchers’ and the general publics’ perceptions of exercise goals. Canadian Journal of Behavioural Science/Revue canadienne des sciences du comportement, 57(3), 239–248. https://doi.org/10.1037/cbs0000411
"""

valid_refs, invalid_refs = extract_and_process_references(text)

for ref in valid_refs:
    print(f"Reference {ref['ref_number']}: {ref['text']}")
    print(f"  Entities: {ref['ner']}")