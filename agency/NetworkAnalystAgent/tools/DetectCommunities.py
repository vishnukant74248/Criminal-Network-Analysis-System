from agency_swarm.tools import BaseTool
from pydantic import Field
import networkx as nx
import json

class DetectCommunities(BaseTool):
    """
    Detects communities (criminal clusters / gangs) in the network using
    the Louvain or Girvan-Newman algorithm and returns cluster membership.
    """
    algorithm: str = Field(
        default="louvain",
        description="Community detection algorithm: 'louvain' or 'girvan_newman'."
    )
    max_communities: int = Field(
        default=10,
        description="Maximum number of communities to return."
    )

    def run(self):
        try:
            G = nx.karate_club_graph()  # Replace with real graph loader
            communities = []

            if self.algorithm == "louvain":
                try:
                    from community import best_partition  # python-louvain
                    partition = best_partition(G)
                    grouped = {}
                    for node, comm_id in partition.items():
                        grouped.setdefault(comm_id, []).append(node)
                    communities = [
                        {"community_id": cid, "members": members, "size": len(members)}
                        for cid, members in sorted(grouped.items(), key=lambda x: -len(x[1]))
                    ][:self.max_communities]
                except ImportError:
                    # Fallback to greedy modularity
                    from networkx.algorithms.community import greedy_modularity_communities
                    raw = list(greedy_modularity_communities(G))
                    communities = [
                        {"community_id": i, "members": list(c), "size": len(c)}
                        for i, c in enumerate(sorted(raw, key=len, reverse=True))
                    ][:self.max_communities]

            elif self.algorithm == "girvan_newman":
                from networkx.algorithms.community import girvan_newman
                comp = girvan_newman(G)
                first_level = next(comp)
                communities = [
                    {"community_id": i, "members": list(c), "size": len(c)}
                    for i, c in enumerate(sorted(first_level, key=len, reverse=True))
                ][:self.max_communities]
            else:
                return f"Unknown algorithm '{self.algorithm}'. Use 'louvain' or 'girvan_newman'."

            return json.dumps({
                "algorithm": self.algorithm,
                "total_communities": len(communities),
                "communities": communities
            }, indent=2)

        except Exception as e:
            return f"Error detecting communities: {str(e)}"
