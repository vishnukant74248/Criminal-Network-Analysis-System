"""
SENTINEL Agency — Criminal Network Analysis Multi-Agent System
CEO Prime Agent commands: NetworkAnalystAgent, DataIntelAgent,
ThreatScoringAgent, and ReportAgent.
"""

import os
import sys
from dotenv import load_dotenv

# Ensure agency package directory is in sys.path
agency_dir = os.path.dirname(os.path.abspath(__file__))
if agency_dir not in sys.path:
    sys.path.insert(0, agency_dir)

# Load environment variables from .env if present
env_path = os.path.join(agency_dir, ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)

from agency_swarm import Agency
from CEO import CEO
from NetworkAnalystAgent import NetworkAnalystAgent
from DataIntelAgent import DataIntelAgent
from ThreatScoringAgent import ThreatScoringAgent
from ReportAgent import ReportAgent

# ── Instantiate agents ────────────────────────────────────────────
ceo               = CEO()
network_analyst   = NetworkAnalystAgent()
data_intel        = DataIntelAgent()
threat_scorer     = ThreatScoringAgent()
reporter          = ReportAgent()

# ── Define the agency and communication flows ─────────────────────
# Positional arguments: Entry-point agents that can interact with the user (CEO Prime Agent).
# communication_flows: Allowed directed communication channels between agents.
flows = [
    (ceo, network_analyst),        # CEO → NetworkAnalystAgent
    (ceo, data_intel),             # CEO → DataIntelAgent
    (ceo, threat_scorer),          # CEO → ThreatScoringAgent
    (ceo, reporter),               # CEO → ReportAgent
    (network_analyst, data_intel), # NetworkAnalyst can request data from DataIntel
    (threat_scorer, data_intel),   # ThreatScorer can request data from DataIntel
    (reporter, threat_scorer),     # Reporter can pull scores from ThreatScorer
    (reporter, network_analyst),   # Reporter can pull network analysis
]

manifesto_path = os.path.join(agency_dir, "agency_manifesto.md")

agency = Agency(
    ceo,
    communication_flows=flows,
    shared_instructions=manifesto_path if os.path.exists(manifesto_path) else None,
)

if __name__ == "__main__":
    agency.run_demo()   # Launches interactive terminal chat
