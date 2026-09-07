from agency_swarm import Agent
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
            instructions="./instructions.md",
            tools=[AnalyzeNetwork, ComputeCentrality, DetectCommunities],
            temperature=0.2,
            max_prompt_tokens=20000,
        )
