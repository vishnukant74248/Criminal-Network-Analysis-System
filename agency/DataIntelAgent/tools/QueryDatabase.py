from agency_swarm.tools import BaseTool
from pydantic import Field
import json

class QueryDatabase(BaseTool):
    """
    Queries the SENTINEL criminal intelligence database for persons,
    locations, events, or relationships.
    """
    query_type: str = Field(
        description="Type of query: 'person', 'location', 'event', or 'relationship'."
    )
    filters: str = Field(
        default="{}",
        description="JSON string of filter criteria, e.g. '{\"name\": \"John Doe\"}' or '{\"threat_level\": \"HIGH\"}'."
    )
    limit: int = Field(default=20, description="Maximum number of results to return.")

    def run(self):
        try:
            filters = json.loads(self.filters)
        except json.JSONDecodeError:
            return "Error: 'filters' must be a valid JSON string."

        # Placeholder — replace with real DB query via sentinel backend
        mock_data = {
            "person": [
                {"id": "P001", "name": "John Doe", "threat_level": "HIGH", "known_associates": ["P002", "P005"]},
                {"id": "P002", "name": "Jane Smith", "threat_level": "MEDIUM", "known_associates": ["P001"]},
            ],
            "location": [
                {"id": "L001", "name": "Warehouse 7, Mumbai", "activity_count": 12, "last_active": "2026-09-01"},
                {"id": "L002", "name": "Safe House, Delhi", "activity_count": 5, "last_active": "2026-08-28"},
            ],
            "event": [
                {"id": "E001", "type": "Meeting", "date": "2026-09-01", "participants": ["P001", "P002"], "location": "L001"},
                {"id": "E002", "type": "Transaction", "date": "2026-08-15", "amount": "₹5,00,000", "parties": ["P001"]},
            ],
            "relationship": [
                {"source": "P001", "target": "P002", "type": "associate", "strength": 0.85},
                {"source": "P001", "target": "P005", "type": "financial_link", "strength": 0.72},
            ],
        }

        if self.query_type not in mock_data:
            return f"Unknown query_type '{self.query_type}'. Use: person, location, event, relationship."

        results = mock_data[self.query_type]

        # Apply simple filter matching
        if filters:
            results = [
                r for r in results
                if all(str(r.get(k, "")).lower() == str(v).lower() for k, v in filters.items())
            ] or results  # fallback to all if no match

        results = results[:self.limit]
        return json.dumps({"query_type": self.query_type, "count": len(results), "results": results}, indent=2)
