import pandas as pd
from tools.data_sources.base import DataSource

class CSVDataSource(DataSource):
    def __init__(self, file_path):
        self.df = pd.read_csv(file_path)

    def query(self, query: str):
        try:
            result = self.df.query(query)

            return {
                "columns": list(result.columns),
                "rows": result.values.tolist(),
                "row_count": len(result)
            }

        except Exception as e:
            return {"error": str(e)}