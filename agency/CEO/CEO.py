from agency_swarm import Agent

class CEO(Agent):
    def __init__(self):
        super().__init__(
            name="CEO",
            description=(
                "The CEO Prime Agent — top-level commander of the SENTINEL "
                "Criminal Network Analysis System. Receives investigation goals "
                "from the user, decomposes them into tasks, and delegates to "
                "specialist sub-agents: NetworkAnalystAgent, DataIntelAgent, "
                "ThreatScoringAgent, and ReportAgent."
            ),
            instructions="./instructions.md",
            tools=[],
            temperature=0.3,
            max_prompt_tokens=25000,
        )
