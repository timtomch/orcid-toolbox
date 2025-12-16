from src.orcid_data import fetch_orcid_data

df, raw_data = fetch_orcid_data("0000-0002-5210-7083")
name = df['name'].iloc[0] if not df.empty and 'name' in df.columns else ''
print(f"Name : {name}")
print(f"Total publications: {len(df)}")
for _, row in df.iterrows():
    title = row.get('title') if 'title' in row else None
    doi = row.get('doi') if 'doi' in row else None
    print(f"- {title} (DOI: {doi or 'N/A'})")