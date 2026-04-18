from abc import ABC, abstractmethod

class DataSource(ABC):

    @abstractmethod
    def query(self, query: str):
        pass