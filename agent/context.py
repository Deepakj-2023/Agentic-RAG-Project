# context.py :  Memory and Context management for the agent

from typing import List, Dict

class Context:
    def __init__(self):
        self.history: List[Dict] = []

    def add(self, step_data: Dict):
        self.history.append(step_data)

    def get(self) -> List[Dict]:
        return self.history

    def __str__(self):
        return str(self.history)