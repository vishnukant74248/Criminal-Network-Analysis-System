from agency_swarm.tools import BaseTool
from pydantic import Field
import networkx as nx
import json
import sys
import os

# Allow importing from backend if available
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../sentinel/backend"))
if os.path.exists(backend_path) and backend_path not in sys.path:
    sys.path.insert(0, backend_path)

class AnalyzeNetwork(BaseTool):
    """
    Analyzes the criminal network graph and returns a summary of nodes,
    edges, density, and top connected entities.
    """
    entity_id: str = Field(
        default="",
        description="Optional. If provided, analyze the local neighborhood of this specific entity."
    )
    depth: int = Field(
        default=2,
        description="Depth of neighborhood to explore around the entity (1-3). Default is 2."
    )

    def run(self):
        try:
            # Build a sample graph (in production this connects to the SENTINEL backend)
            G = nx.karate_club_graph()  # placeholder — replace with real data loader

            analysis = {
                "total_nodes": G.number_of_nodes(),
                "total_edges": G.number_of_edges(),
                "density": round(nx.density(G), 4),
                "is_connected": nx.is_connected(G),
                "average_clustering": round(nx.average_clustering(G), 4),
                "top_degree_nodes": sorted(
                    dict(G.degree()).items(), key=lambda x: x[1], reverse=True
                )[:5],
            }

            if self.entity_id:
                if self.entity_id.isdigit() and int(self.entity_id) in G.nodes:
                    node = int(self.entity_id)
                    neighbors = list(G.neighbors(node))
                    analysis["entity_focus"] = {
                        "entity_id": self.entity_id,
                        "degree": G.degree(node),
                        "neighbors": neighbors[:10],
                    }
                else:
                    analysis["entity_focus"] = {"error": f"Entity '{self.entity_id}' not found in graph."}

            return json.dumps(analysis, indent=2)

        except Exception as e:
            return f"Error analyzing network: {str(e)}"
