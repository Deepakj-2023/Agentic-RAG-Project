from utils.vector_store import VectorStore

# Initialize once (shared instance)
store = VectorStore()

def search_documents_tool(query: str) -> dict:
    """
    Tool for LLM agent
    """
    results = store.search(query)

    return {
        "query": query,
        "results": results
    }