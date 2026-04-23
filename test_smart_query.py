from tools.query_tool import query_data

def test_sql_intent():
    print("\n--- Testing SQL Intent ---")
    intent = "Find the player who has scored the most runs in PSL history"
    result = query_data("sql", intent)
    print(f"Result: {result}")

def test_pandas_intent():
    print("\n--- Testing Pandas Intent ---")
    intent = "Find the top 5 run scorers in IPL history"
    result = query_data("pandas", intent, csv_name="IPL.csv")
    print(f"Result: {result}")

if __name__ == "__main__":
    test_sql_intent()
    test_pandas_intent()
