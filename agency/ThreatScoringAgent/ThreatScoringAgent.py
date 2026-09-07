import os
from agency_swarm import Agent, ModelSettings
from .tools.ScoreThreat import ScoreThreat
from .tools.GenerateAlert import GenerateAlert
from .tools.TrackEscalation import TrackEscalation

class ThreatScoringAgent(Agent):
    def __init__(self):
        super().__init__(
            name="ThreatScoringAgent",
            description=(
                "Specialist in risk assessment and threat scoring. Computes "
                "threat scores (0–100) for persons, groups, and locations, "
                "classifies threat levels, and triggers CRITICAL alerts."
            ),
            instructions=os.path.join(os.path.dirname(__file__), "instructions.md"),
            tools=[ScoreThreat, GenerateAlert, TrackEscalation],
            model_settings=ModelSettings(temperature=0.2, max_tokens=20000),
        )
