from agency_swarm import Agent
from .tools.GenerateReport import GenerateReport
from .tools.ExportReport import ExportReport

class ReportAgent(Agent):
    def __init__(self):
        super().__init__(
            name="ReportAgent",
            description=(
                "Specialist in generating investigation reports and executive "
                "summaries. Compiles findings from all agents into structured, "
                "human-readable reports with timelines and recommendations."
            ),
            instructions="./instructions.md",
            tools=[GenerateReport, ExportReport],
            temperature=0.4,
            max_prompt_tokens=20000,
        )
