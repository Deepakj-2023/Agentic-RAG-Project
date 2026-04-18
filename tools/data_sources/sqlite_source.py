import sqlite3
from tools.data_sources.base import DataSource

class SQLiteDataSource(DataSource):
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path)

    def query(self, query: str):
        try:
            cursor = self.conn.cursor()
            cursor.execute(query)

            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]

            return {
                "columns": columns,
                "rows": rows,
                "row_count": len(rows)
            }

        except Exception as e:
            return {"error": str(e)}