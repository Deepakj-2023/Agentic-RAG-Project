import pandas as pd
import sqlite3
import os
import json
from langchain_core.messages import SystemMessage, HumanMessage
from agent.llm_brain import llm, load_compact_schema

# Cache for dataframes
_dataframes = {}

# ────────────────────────────────────────────────────────────
# SMART CODE GENERATOR
# ────────────────────────────────────────────────────────────

QUERY_GEN_PROMPT = """
You are a Data Scientist specialized in Sports Analytics.
Your task is to translate a natural language "intent" into executable code ({query_type}).

DATASETS AVAILABLE:
{schema}

RULES:
1. If query_type is "sql", output ONLY a valid SQLite SELECT statement.
   - ⚠️ IMPORTANT: Always use double quotes for column names that start with numbers or contain special characters (e.g., "4s", "6s", "Match Date").
2. If query_type is "pandas", output ONLY valid Python code using a dataframe named 'df'.
   - **IMPORTANT**: For multi-line code, you **MUST** assign the final answer to a variable named `result`.
   - You can use sorting, grouping, and aggregations.
   - Example: result = df.sort_values('runs_batter', ascending=False).head(5)
   - Example: result = df[df['batter'] == 'Virat Kohli']
3. ALWAYS use double quotes for column names that start with numbers or contain spaces.
   - ✅ Correct: SELECT "Player", "Runs", "4s", "6s", "Match Date" FROM psl_highest_individual_score
   - ❌ Incorrect: SELECT Player, Runs, 4s, 6s, Match Date FROM psl_highest_individual_score
4. DO NOT include markdown formatting or explanations.

Output only the raw code string.
"""

def _generate_query_code(intent: str, query_type: str, error_msg: str = None, previous_code: str = None) -> str:
    schema = load_compact_schema()
    
    prompt = QUERY_GEN_PROMPT.format(
        query_type=query_type,
        schema=schema
    )
    
    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content=f"Intent: {intent}")
    ]

    if error_msg and previous_code:
        messages.append(HumanMessage(content=f"Your previous code: {previous_code}\n\nFAILED with error: {error_msg}\n\nPlease fix the code and return only the corrected version."))
    
    response = llm.invoke(messages)
    code = response.content.strip()
    # Clean up common LLM artifacts
    code = code.replace("```sql", "").replace("```python", "").replace("```", "").strip()
    if code.lower().startswith("query_type:"):
        code = code.split("\n", 1)[-1].strip()
    return code

# ────────────────────────────────────────────────────────────
# EXECUTORS
# ────────────────────────────────────────────────────────────

def _query_pandas(csv_name: str, query: str):
    file_path = f"data/structure_data/{csv_name}"
    if not os.path.exists(file_path):
        file_path = f"data/{csv_name}"
        if not os.path.exists(file_path):
            return {"error": f"CSV file {csv_name} not found."}
    
    try:
        if csv_name not in _dataframes:
            print(f"[LOAD] {csv_name}...")
            _dataframes[csv_name] = pd.read_csv(file_path, low_memory=False, encoding="latin1")
        
        df = _dataframes[csv_name]
        
        # Use exec to allow multi-line pandas code
        local_vars = {"df": df, "pd": pd, "result": None}
        try:
            # If the query is multi-line or contains assignments, use exec
            if "\n" in query or "=" in query:
                exec(query, {}, local_vars)
                result = local_vars.get("result")
            else:
                result = eval(query, {"df": df, "pd": pd})
        except Exception as e:
            # Fallback to df.query if it's just a filter string
            try:
                result = df.query(query)
            except:
                cols = list(df.columns)
                return {"error": f"Pandas execution failed: {e}. Columns: {cols[:15]}"}
        
        if result is None or (isinstance(result, pd.DataFrame) and len(result) == 0):
            return {"source": csv_name, "message": "No results found.", "row_count": 0, "query_used": query}

        # Convert result to a format suitable for JSON
        if isinstance(result, pd.DataFrame):
            output_rows = result.head(5).values.tolist()
            output_cols = list(result.columns)
            row_count = len(result)
        elif isinstance(result, pd.Series):
            # If it's a single row (Series), columns are the index, rows are the values
            output_cols = list(result.index)
            output_rows = [result.tolist()]
            row_count = 1
        else:
            output_rows = [[str(result)]]
            output_cols = ["result"]
            row_count = 1

        return {
            "source": csv_name,
            "columns": output_cols,
            "rows": output_rows,
            "row_count": row_count,
            "query_used": query
        }
    except Exception as e:
        return {"error": str(e)}

def _query_sql(sql_query: str):
    db_path = "data/sports_data.db"
    if not os.path.exists(db_path):
        return {"error": "SQLite database not found."}
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(sql_query)
        
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        conn.close()
        
        if len(rows) == 0:
            return {"source": "SQLite DB", "message": "No results found.", "row_count": 0, "query_used": sql_query}

        return {
            "source": "SQLite DB",
            "columns": columns,
            "rows": rows[:5],
            "row_count": len(rows),
            "query_used": sql_query
        }
    except Exception as e:
        return {"error": str(e)}

# ────────────────────────────────────────────────────────────
# MAIN TOOL ENTRY
# ────────────────────────────────────────────────────────────

def query_data(query_type: str, intent: str, csv_name: str = None):
    """
    Smart query tool that translates intent to code then executes.
    Includes self-correction logic for code execution errors.
    """
    print(f"[SMART-TOOL] Translating intent: {intent}")
    
    last_error = None
    generated_code = None

    for attempt in range(2): # Try up to 2 times
        try:
            # 1. Generate code from intent (with error feedback if this is a retry)
            generated_code = _generate_query_code(intent, query_type, error_msg=last_error, previous_code=generated_code)
            
            if attempt > 0:
                print(f"[SMART-TOOL] Retry Attempt {attempt} - New {query_type}: {generated_code}")
            else:
                print(f"[SMART-TOOL] Generated {query_type}: {generated_code}")
            
            # 2. Execute
            if query_type == "sql":
                result = _query_sql(generated_code)
            elif query_type == "pandas":
                if not csv_name:
                    return {"error": "csv_name is required for pandas queries."}
                result = _query_pandas(csv_name, generated_code)
            else:
                return {"error": f"Invalid query_type: {query_type}"}

            # 3. Check for execution errors to trigger retry
            if "error" in result:
                last_error = result["error"]
                print(f"[SMART-TOOL] Execution failed: {last_error}. Retrying...")
                continue
            
            return result

        except Exception as e:
            last_error = str(e)
            print(f"[SMART-TOOL] Unexpected error: {last_error}. Retrying...")
            
    return {"error": f"Smart Tool failed after retries. Last error: {last_error}"}