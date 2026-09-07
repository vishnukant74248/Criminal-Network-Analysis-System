from agency_swarm.tools import BaseTool
from pydantic import Field
import networkx as nx
import json

class ComputeCentrality(BaseTool):
    """
    Computes centrality metrics (degree, betweenness, closeness, eigenvector)
    for all nodes in the criminal network and returns the top-N most central nodes.
    """
    top_n: int = Field(default=10, description="Number of top nodes to return per metric.")
    metric: str = Field(
        default="all",
        description="Centrality metric to compute: 'degree', 'betweenness', 'closeness', 'eigenvector', or 'all'."
    )

    def run(self):
        try:
            G = nx.karate_club_graph()  # Replace with real graph loader
            results = {}

            metrics_map = {
                "degree":      lambda g: nx.degree_centrality(g),
                "betweenness": lambda g: nx.betweenness_centrality(g),
                "closeness":   lambda g: nx.closeness_centrality(g),
                "eigenvector": lambda g: nx.eigenvector_centrality(g, max_iter=1000),
            }

            selected = metrics_map.keys() if self.metric == "all" else [self.metric]

            for name in selected:
                if name not in metrics_map:
                    results[name] = f"Unknown metric '{name}'"
                    continue
                scores = metrics_map[name](G)
                top = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:self.top_n]
                results[name] = [{"node": str(n), "score": round(s, 4)} for n, s in top]

            return json.dumps(results, indent=2)

        except Exception as e:
            return f"Error computing centrality: {str(e)}"
