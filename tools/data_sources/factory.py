from tools.data_sources.sqlite_source import SQLiteDataSource
from tools.data_sources.csv_source import CSVDataSource

def get_data_source(db_type: str):
    
    if db_type == "sqlite":
        return SQLiteDataSource("data/financials.db")

    elif db_type == "csv":
        return CSVDataSource("data/financials.csv")

    else:
        raise ValueError(f"Unsupported DB type: {db_type}")