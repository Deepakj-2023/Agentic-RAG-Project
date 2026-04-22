from utils.vector_store import vector_store_instance

def search_docs(query: str) -> dict:
    """
    Search for information in the unstructured document store (match reports, summaries).
    Returns top relevant chunks with source filename and URL.
    """
    results = vector_store_instance.search(query)

    if not results:
        return {"query": query, "message": "No relevant documents found in our local reports. Try web_search for live info."}

    return {
        "query": query,
        "results": results
    }