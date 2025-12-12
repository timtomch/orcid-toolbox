from src.orcid_data import fetch_orcid_data

data = fetch_orcid_data("0000-0002-5210-7083")
print(f"Name : {data['name']}")
print(f"Total publications: {data['count']}")
for pub in data["publications"]:
    print(f"- {pub['title']} (DOI: {pub.get('doi', 'N/A')})")