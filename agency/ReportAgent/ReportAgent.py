import os
from agency_swarm import Agent, ModelSettings
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
            instructions=os.path.join(os.path.dirname(__file__), "instructions.md"),
            tools=[GenerateReport, ExportReport],
            model_settings=ModelSettings(temperature=0.4, max_tokens=20000),
        )
