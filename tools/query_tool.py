from tools.data_sources.factory import get_data_source
from utils.config import DB_TYPE

data_source = get_data_source(DB_TYPE)

def query_data(query: str):
    """
    LLM-facing tool function
    """

    result = data_source.query(query)

    return result