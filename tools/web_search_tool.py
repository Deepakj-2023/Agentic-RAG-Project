import os
from tavily import TavilyClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize client
client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

def web_search(query: str):
    """
    Perform web search using Tavily API

    Input:
        query (str): short search query

    Output:
        dict: top 5 results with snippet, url, date
    """

    try:
        response = client.search(
            query=query,
            search_depth="basic",   # fast + cheap
            max_results=5
        )

        results = []

        for item in response.get("results", []):
            results.append({
                "title": item.get("title"),
                "snippet": item.get("content"),
                "url": item.get("url"),
                "published_date": item.get("published_date")
            })

        if not results:
            return {"query": query, "message": "No relevant web results found. Try search_docs for historical data."}

        return {
            "query": query,
            "results": results
        }

    except Exception as e:
        return {
            "error": str(e)
        }