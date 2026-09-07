from agency_swarm.tools import BaseTool
from pydantic import Field
from datetime import datetime
import json

class TrackEscalation(BaseTool):
    """
    Tracks threat score changes over time for an entity and flags escalations
    where the score has increased significantly.
    """
    entity_id: str = Field(description="Entity ID to track.")
    current_score: float = Field(description="Current computed threat score.")
    previous_score: float = Field(
        default=0.0,
        description="Previous threat score for comparison. 0.0 if first assessment."
    )

    def run(self):
        delta = round(self.current_score - self.previous_score, 1)
        pct_change = round((delta / self.previous_score * 100), 1) if self.previous_score > 0 else 100.0

        escalated = delta >= 15  # 15-point jump = escalation

        record = {
            "entity_id": self.entity_id,
            "timestamp": datetime.now().isoformat(),
            "previous_score": self.previous_score,
            "current_score": self.current_score,
            "delta": delta,
            "percent_change": f"{pct_change}%",
            "escalation_detected": escalated,
            "escalation_severity": (
                "SEVERE" if delta >= 30 else
                "MODERATE" if delta >= 15 else
                "NONE"
            ),
            "action_required": (
                "IMMEDIATE — Notify commanding officer." if delta >= 30 else
                "URGENT — Increase surveillance." if delta >= 15 else
                "No escalation action needed."
            )
        }

        # Append to escalation log
        import os
        log_dir = os.path.join(os.path.dirname(__file__), "../../../alerts")
        os.makedirs(log_dir, exist_ok=True)
        with open(os.path.join(log_dir, "escalation_log.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

        return json.dumps(record, indent=2)
