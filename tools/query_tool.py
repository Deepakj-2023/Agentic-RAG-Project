import pandas as pd
import sqlite3
import os

# Cache for dataframes
_dataframes = {}

def _query_pandas(csv_name: str, query: str):
    file_path = f"data/{csv_name}"
    if not os.path.exists(file_path):
        return {"error": f"CSV file {csv_name} not found in data/ folder."}
    
    try:
        if csv_name not in _dataframes:
            print(f"Loading {csv_name} into memory...")
            _dataframes[csv_name] = pd.read_csv(file_path, low_memory=False)
        
        df = _dataframes[csv_name]
        try:
            result = df.query(query)
        except Exception as e:
            cols = list(df.columns)
            return {"error": f"Pandas query failed: {e}. Available columns are: {cols}"}
        
        if len(result) == 0:
            return {"source": csv_name, "message": "No results found. Try a broader query or different tool.", "row_count": 0}

        return {
            "source": csv_name,
            "columns": list(result.columns),
            "rows": result.head(5).values.tolist(),
            "row_count": len(result)
        }
    except Exception as e:
        return {"error": str(e)}

def _query_sql(sql_query: str):
    db_path = "data/sports_data.db"
    if not os.path.exists(db_path):
        return {"error": "SQLite database not found. Run scripts/setup_data.py first."}
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(sql_query)
        
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        conn.close()
        
        if len(rows) == 0:
            return {"source": "SQLite DB", "message": "No results found in the database. Try search_docs or web_search.", "row_count": 0}

        return {
            "source": "SQLite DB",
            "columns": columns,
            "rows": rows[:5],
            "row_count": len(rows)
        }
    except Exception as e:
        return {"error": str(e)}

def query_data(query_type: str, query_input: str, csv_name: str = None):
    """
    Unified query tool for structured data.
    
    Args:
        query_type (str): 'sql' or 'pandas'
        query_input (str): The SQL query string or Pandas query string.
        csv_name (str, optional): The name of the CSV file if query_type is 'pandas'.
    """
    if query_type == "sql":
        return _query_sql(query_input)
    elif query_type == "pandas":
        if not csv_name:
            return {"error": "csv_name is required for pandas queries."}
        return _query_pandas(csv_name, query_input)
    else:
        return {"error": f"Invalid query_type: {query_type}. Use 'sql' or 'pandas'."}