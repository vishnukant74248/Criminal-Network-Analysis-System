from agency_swarm.tools import BaseTool
from pydantic import Field
import json
import os

class IngestData(BaseTool):
    """
    Ingests new criminal intelligence data from a JSON or CSV file
    into the SENTINEL system.
    """
    file_path: str = Field(description="Absolute or relative path to the data file (.json or .csv).")
    data_type: str = Field(
        default="person",
        description="Type of data being ingested: 'person', 'location', 'event', or 'relationship'."
    )

    def run(self):
        if not os.path.exists(self.file_path):
            return f"Error: File not found at '{self.file_path}'."

        ext = os.path.splitext(self.file_path)[1].lower()

        try:
            if ext == ".json":
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                record_count = len(data) if isinstance(data, list) else 1
            elif ext == ".csv":
                import csv
                with open(self.file_path, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    data = list(reader)
                record_count = len(data)
            else:
                return f"Unsupported file format '{ext}'. Use .json or .csv."

            # Placeholder: In production, write to SENTINEL DB here
            return json.dumps({
                "status": "success",
                "file": self.file_path,
                "data_type": self.data_type,
                "records_ingested": record_count,
                "message": f"Successfully read {record_count} records. Ready for database insertion."
            }, indent=2)

        except Exception as e:
            return f"Error ingesting data: {str(e)}"
