from agency_swarm.tools import BaseTool
from pydantic import Field
import json

class ScoreThreat(BaseTool):
    """
    Computes a threat score (0-100) for a given entity based on
    network centrality, known associations, activity count, and criminal history.
    """
    entity_id: str = Field(description="The ID of the entity to score (person, group, or location).")
    entity_type: str = Field(
        default="person",
        description="Type of entity: 'person', 'group', or 'location'."
    )
    centrality_score: float = Field(
        default=0.0,
        description="Centrality score from NetworkAnalystAgent (0.0 to 1.0)."
    )
    known_associates: int = Field(
        default=0,
        description="Number of known criminal associates."
    )
    incident_count: int = Field(
        default=0,
        description="Number of criminal incidents linked to this entity."
    )
    prior_convictions: int = Field(
        default=0,
        description="Number of prior convictions."
    )

    def run(self):
        try:
            # Weighted scoring formula
            centrality_weight    = 0.30
            associates_weight    = 0.25
            incidents_weight     = 0.30
            convictions_weight   = 0.15

            centrality_points  = min(self.centrality_score * 100, 100) * centrality_weight
            associates_points  = min(self.known_associates * 5, 100) * associates_weight
            incidents_points   = min(self.incident_count * 10, 100) * incidents_weight
            convictions_points = min(self.prior_convictions * 15, 100) * convictions_weight

            total_score = round(
                centrality_points + associates_points + incidents_points + convictions_points, 1
            )

            # Classify threat level
            if total_score >= 75:
                level = "CRITICAL"
            elif total_score >= 50:
                level = "HIGH"
            elif total_score >= 25:
                level = "MEDIUM"
            else:
                level = "LOW"

            confidence = min(
                60 + (self.incident_count * 5) + (self.prior_convictions * 3), 99
            )

            return json.dumps({
                "entity_id": self.entity_id,
                "entity_type": self.entity_type,
                "threat_score": total_score,
                "threat_level": level,
                "confidence": f"{confidence}%",
                "breakdown": {
                    "centrality_contribution": round(centrality_points, 2),
                    "associates_contribution": round(associates_points, 2),
                    "incidents_contribution": round(incidents_points, 2),
                    "convictions_contribution": round(convictions_points, 2),
                },
                "recommendation": (
                    "Immediate action required — escalate to command."
                    if level == "CRITICAL" else
                    "Flag for surveillance and monitoring."
                    if level == "HIGH" else
                    "Add to watch list."
                    if level == "MEDIUM" else
                    "Monitor passively."
                )
            }, indent=2)

        except Exception as e:
            return f"Error scoring threat: {str(e)}"
