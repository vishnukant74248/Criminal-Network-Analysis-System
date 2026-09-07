from agency_swarm.tools import BaseTool
from pydantic import Field
from datetime import datetime
import json
import os

class ExportReport(BaseTool):
    """
    Exports a generated report to a markdown file in the reports directory.
    """
    report_id: str = Field(description="The report ID returned by GenerateReport.")
    report_content: str = Field(description="The full markdown report content to export.")
    format: str = Field(
        default="markdown",
        description="Export format: 'markdown' (saves as .md) or 'json' (saves as .json)."
    )

    def run(self):
        try:
            reports_dir = os.path.join(os.path.dirname(__file__), "../../../reports")
            os.makedirs(reports_dir, exist_ok=True)

            if self.format == "markdown":
                filename = f"{self.report_id}.md"
                filepath = os.path.join(reports_dir, filename)
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(self.report_content)
            elif self.format == "json":
                filename = f"{self.report_id}.json"
                filepath = os.path.join(reports_dir, filename)
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump({
                        "report_id": self.report_id,
                        "exported_at": datetime.now().isoformat(),
                        "content": self.report_content
                    }, f, indent=2)
            else:
                return f"Unsupported format '{self.format}'. Use 'markdown' or 'json'."

            return json.dumps({
                "status": "success",
                "report_id": self.report_id,
                "file": filepath,
                "format": self.format
            }, indent=2)

        except Exception as e:
            return f"Error exporting report: {str(e)}"
