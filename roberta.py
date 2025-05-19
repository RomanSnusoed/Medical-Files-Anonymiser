from transformers import pipeline

class XlmRobertaNER:
    def __init__(self, supported_languages=None):
        self.ner_pipeline = pipeline("ner", model="Davlan/xlm-roberta-base-ner-hrl", grouped_entities=True)
        self.supported_languages = supported_languages or ["en", "de", "uk", "ru"]

    def analyze(self, text):
        if not text:
            return []

       
        print(f"XlmRobertaNER analyzing text: {text}")

        ner_results = self.ner_pipeline(text)
        results = []
        for entity in ner_results:
            label = entity["entity_group"].upper()
            if label in ["PER", "LOC", "ORG", "MISC"]:
                results.append({
                    "type": self.map_entity(label),
                    "start": entity["start"],
                    "end": entity["end"],
                    "text": text[entity["start"]:entity["end"]],
                    "score": entity.get("score", 0.85)
                })
        return results

    def map_entity(self, label):
        mapping = {
            "PER": "PERSON",
            "LOC": "LOCATION",
            "ORG": "ORGANIZATION",
            "MISC": "OTHER"
        }
        return mapping.get(label, "OTHER")