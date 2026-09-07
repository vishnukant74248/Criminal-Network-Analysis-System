import os
from agency_swarm import Agent, ModelSettings
from .tools.AnalyzeNetwork import AnalyzeNetwork
from .tools.ComputeCentrality import ComputeCentrality
from .tools.DetectCommunities import DetectCommunities

class NetworkAnalystAgent(Agent):
    def __init__(self):
        super().__init__(
            name="NetworkAnalystAgent",
            description=(
                "Specialist in criminal network graph analysis. Computes "
                "centrality metrics, detects communities, identifies key nodes, "
                "and traces relationships in the criminal network graph."
            ),
            instructions=os.path.join(os.path.dirname(__file__), "instructions.md"),
            tools=[AnalyzeNetwork, ComputeCentrality, DetectCommunities],
            model_settings=ModelSettings(temperature=0.2, max_tokens=20000),
        )
