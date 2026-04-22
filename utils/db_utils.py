import sqlite3
import os

def get_dynamic_schema():
    db_path = r"D:\AgenticRAG\Proadapt-Project\data\sports_data.db"

    if not os.path.exists(db_path):
        return "Database not found."

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        schema_info = []

        for (table_name,) in tables:

            # Get columns
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            col_names = [col[1] for col in columns]

            table_desc = f"- {table_name} ({', '.join(col_names)})"

            # Add sample for ALL tables (optional)
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 1;")
            sample = cursor.fetchone()

            if sample:
                table_desc += f"\n  Sample: {sample}\n"

            schema_info.append(table_desc)

        conn.close()

        return schema_info

    except Exception as e:
        return f"Error fetching schema: {str(e)}"

print(f" answer{ get_dynamic_schema()}")