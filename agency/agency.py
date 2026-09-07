"""
SENTINEL Agency — Criminal Network Analysis Multi-Agent System
CEO Prime Agent commands: NetworkAnalystAgent, DataIntelAgent,
ThreatScoringAgent, and ReportAgent.
"""

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
# Format: [sender, receiver] means sender CAN communicate with receiver.
# Top-level entries (single agent) means that agent can talk to the USER.
agency = Agency(
    [
        ceo,                          # CEO talks to the user
        [ceo, network_analyst],       # CEO → NetworkAnalystAgent
        [ceo, data_intel],            # CEO → DataIntelAgent
        [ceo, threat_scorer],         # CEO → ThreatScoringAgent
        [ceo, reporter],              # CEO → ReportAgent
        [network_analyst, data_intel],# NetworkAnalyst can request data from DataIntel
        [threat_scorer, data_intel],  # ThreatScorer can request data from DataIntel
        [reporter, threat_scorer],    # Reporter can pull scores from ThreatScorer
        [reporter, network_analyst],  # Reporter can pull network analysis
    ],
    shared_instructions="agency_manifesto.md",
    temperature=0.3,
    max_prompt_tokens=25000,
)

if __name__ == "__main__":
    agency.run_demo()   # Launches interactive terminal chat
