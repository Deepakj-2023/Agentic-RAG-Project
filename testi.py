from tools.web_search_tool import web_search

if __name__ == "__main__":
    query = "Complete each match schedule and stats in FIFA World Cup 2022"

    result = web_search(query)

    print("\nWeb Search Result:\n")
    for r in result["results"]:
        print(f"Title: {r['title']}")
        print(f"Snippet: {r['snippet']}")
        print(f"URL: {r['url']}")
        print(f"Date: {r['published_date']}")
        print("-" * 50)