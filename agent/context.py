# context.py :  Memory and Context management for the agent

from typing import List, Dict
import json

class Context:
    def __init__(self):
        self.history: List[Dict] = []

    def add(self, step_data: Dict):
        self.history.append(step_data)

    def get(self) -> List[Dict]:
        return self.history

    def __str__(self):
        """
        Format context as a clear, readable string so the LLM can
        actually understand what happened in previous steps.
        """
        if not self.history:
            return "No previous steps."

        lines = []
        for step in self.history:
            lines.append(f"Step {step['step']}:")
            lines.append(f"  Tool: {step['tool']}")
            lines.append(f"  Input: {step['input']}")
            # Truncate long outputs
            output_str = json.dumps(step['output']) if isinstance(step['output'], dict) else str(step['output'])
            if len(output_str) > 500:
                output_str = output_str[:500] + "...(truncated)"
            lines.append(f"  Output: {output_str}")
            lines.append("")
        return "\n".join(lines)