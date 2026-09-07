import os
from agency_swarm import Agent, ModelSettings
from .tools.QueryDatabase import QueryDatabase
from .tools.IngestData import IngestData
from .tools.ExtractEntities import ExtractEntities

class DataIntelAgent(Agent):
    def __init__(self):
        super().__init__(
            name="DataIntelAgent",
            description=(
                "Specialist in data ingestion, database queries, and entity "
                "extraction. Fetches and structures raw criminal intelligence "
                "data for other agents to consume."
            ),
            instructions=os.path.join(os.path.dirname(__file__), "instructions.md"),
            tools=[QueryDatabase, IngestData, ExtractEntities],
            model_settings=ModelSettings(temperature=0.1, max_tokens=20000),
        )
