from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class ComplaintAnalysisResult:
    """
    Output container for the NLP pipeline.

    Keep it model-agnostic so you can swap spaCy/transformers later.
    """

    categories: List[str]
    summary: str
    metadata: Dict[str, Any]


class SmartElectricityComplaintAnalyzer:
    """
    Electricity complaint analyzer backed by the spaCy + rule-based pipeline.
    """

    def __init__(self) -> None:
        # Keep the interface stable while allowing the pipeline to evolve.
        from nlp.pipeline import ElectricityComplaintNLP

        self._pipeline = ElectricityComplaintNLP()

    def analyze(self, text: str) -> Dict[str, Any]:
        """
        Analyze complaint text and return a structured dictionary.
        """
        return self._pipeline.analyze(text)

    def analyze_result(self, text: str) -> ComplaintAnalysisResult:
        """
        Same analysis, wrapped in a small dataclass container.
        Useful if you prefer a typed object instead of a dict.
        """
        result = self._pipeline.analyze(text)
        return ComplaintAnalysisResult(
            categories=[result["issue_classification"]["issue_type"]],
            summary=result["preprocessed_text"],
            metadata=result,
        )

