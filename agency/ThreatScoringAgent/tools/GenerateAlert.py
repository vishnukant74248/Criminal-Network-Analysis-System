from agency_swarm.tools import BaseTool
from pydantic import Field
from datetime import datetime
import json

class GenerateAlert(BaseTool):
    """
    Generates a structured alert for a CRITICAL or HIGH threat entity
    and logs it to the alerts file.
    """
    entity_id: str = Field(description="Entity ID triggering the alert.")
    threat_level: str = Field(description="Threat level: 'CRITICAL' or 'HIGH'.")
    threat_score: float = Field(description="Numeric threat score (0-100).")
    reason: str = Field(description="Brief reason for the alert.")
    recommended_action: str = Field(
        default="Escalate to commanding officer immediately.",
        description="Recommended response action."
    )

    def run(self):
        if self.threat_level not in ("CRITICAL", "HIGH"):
            return "Alerts are only generated for CRITICAL or HIGH threat levels."

        alert = {
            "alert_id": f"ALT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "timestamp": datetime.now().isoformat(),
            "entity_id": self.entity_id,
            "threat_level": self.threat_level,
            "threat_score": self.threat_score,
            "reason": self.reason,
            "recommended_action": self.recommended_action,
            "status": "OPEN",
        }

        # Log alert to file
        import os
        alerts_dir = os.path.join(os.path.dirname(__file__), "../../../alerts")
        os.makedirs(alerts_dir, exist_ok=True)
        alerts_file = os.path.join(alerts_dir, "alerts_log.jsonl")
        with open(alerts_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(alert) + "\n")

        return json.dumps({
            "status": "Alert generated and logged.",
            "alert": alert
        }, indent=2)
