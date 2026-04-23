import json
from typing import List, Dict
import uuid

class Context:
    def __init__(self):
        self.sessions: Dict[str, List[Dict]] = {}

    def create_run(self) -> str:
        run_id = str(uuid.uuid4())
        self.sessions[run_id] = []
        return run_id

    def add(self, run_id: str, step_data: Dict):
        self.sessions[run_id].append(step_data)

        # Limit memory
        self.sessions[run_id] = self.sessions[run_id][-6:]

    def to_string(self, run_id: str) -> str:
        history = self.sessions.get(run_id, [])

        if not history:
            return "No previous steps."

        lines = []
        for step in history:
            lines.append(f"Step {step['step']}:")
            lines.append(f"  Tool: {step['tool']}")
            lines.append(f"  Input: {step['input']}")

            output_str = json.dumps(step['output']) if isinstance(step['output'], dict) else str(step['output'])
            if len(output_str) > 500:
                output_str = output_str[:500] + "...(truncated)"

            lines.append(f"  Output: {output_str}")
            lines.append("")

        return "\n".join(lines)