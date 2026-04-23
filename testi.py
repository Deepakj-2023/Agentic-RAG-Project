from tools.web_search_tool import web_search
from tools.search_doc_tool import search_docs
from tools.query_tool import  query_data
if __name__ == "__main__":
    # print("\nWeb Search Tool Test:\n")
    # query1 = "Complete each match schedule and stats in FIFA World Cup 2022"

    # result = web_search(query1)

    # print("\nWeb Search Result:\n")
    # for r in result["results"]:
    #     print(f"Title: {r['title']}")
    #     print(f"Snippet: {r['snippet']}")
    #     print(f"URL: {r['url']}")
    #     print(f"Date: {r['published_date']}")
    #     print("-" * 50)


    # print("\nVector Search Tool Test:\n")
    # query2 = "Explain 2022 FIFA World Cup final"
    # result2 = search_docs(query2)
    # print(result2)  

    print("query tools : sql")
    query3  = "SELECT player, runs FROM psl_most_runs_by_a_player ORDER BY runs DESC LIMIT 5;"
    result3 =  query_data("sql",query3)
    print(result3)      

    print("Query tools : pandas")
    query4 = "..."
    result4  = query_data("pandas",query4,"structure_data/player_stats.csv")
    print(result4)
