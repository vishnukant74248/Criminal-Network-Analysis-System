from agency_swarm.tools import BaseTool
from pydantic import Field
import json
import re

class ExtractEntities(BaseTool):
    """
    Extracts named entities (persons, organizations, locations, dates, amounts)
    from raw intelligence text using pattern matching and NLP.
    """
    text: str = Field(description="Raw intelligence text to extract entities from.")

    def run(self):
        try:
            # Basic regex-based extraction (replace with spaCy/NER in production)
            entities = {
                "persons": [],
                "locations": [],
                "organizations": [],
                "dates": [],
                "amounts": [],
            }

            # Date patterns
            date_pattern = r'\b(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}|\d{4}-\d{2}-\d{2}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4})\b'
            entities["dates"] = re.findall(date_pattern, self.text, re.IGNORECASE)

            # Currency/amount patterns
            amount_pattern = r'(?:₹|Rs\.?|INR|USD|\$)\s?[\d,]+(?:\.\d+)?(?:\s?(?:lakh|crore|million|thousand))?'
            entities["amounts"] = re.findall(amount_pattern, self.text, re.IGNORECASE)

            # Try spaCy if available
            try:
                import spacy
                nlp = spacy.load("en_core_web_sm")
                doc = nlp(self.text)
                for ent in doc.ents:
                    if ent.label_ == "PERSON":
                        entities["persons"].append(ent.text)
                    elif ent.label_ in ("GPE", "LOC"):
                        entities["locations"].append(ent.text)
                    elif ent.label_ == "ORG":
                        entities["organizations"].append(ent.text)
            except (ImportError, OSError):
                # Fallback: capitalized word sequences as possible names
                name_pattern = r'\b([A-Z][a-z]+ (?:[A-Z][a-z]+ )?[A-Z][a-z]+)\b'
                entities["persons"] = list(set(re.findall(name_pattern, self.text)))

            # Deduplicate
            for key in entities:
                entities[key] = list(set(entities[key]))

            return json.dumps({
                "status": "success",
                "entity_count": sum(len(v) for v in entities.values()),
                "entities": entities
            }, indent=2)

        except Exception as e:
            return f"Error extracting entities: {str(e)}"
