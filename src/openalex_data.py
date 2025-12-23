from pyalex import Works

def get_openalex_data(doi=None, title=None, journal=None, author=None):
    """
    Fetches data from OpenAlex for a given DOI or title/journal/author combination.

    Parameters:
    doi (str, optional): The DOI of the work to fetch data for.
    title (str, optional): The title of the work.
    journal (str, optional): The journal name.
    author (str, optional): The author name.

    Returns:
    dict: A dictionary containing the work's data, or None if not found.
    
    Note:
    - If DOI is provided, it will be used directly.
    - If DOI is not provided, you must provide at least a title.
    - Journal and author are optional filters to narrow down results.
    """
    if doi:
        # Use DOI directly
        work = Works()[doi]
        return work if work else None
    
    if not title:
        raise ValueError("Either 'doi' or 'title' must be provided")
    
    # Build search query using title, journal, and/or author
    query = Works().search(title)
    
    # Apply filters if provided
    if journal:
        query = query.filter(host_venue={'display_name': journal})
    
    if author:
        query = query.filter(author={'search': author})
    
    # Get the first result
    results = list(query)
    return results[0] if results else None