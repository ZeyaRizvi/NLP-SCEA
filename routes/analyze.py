import logging
from functools import lru_cache
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from database.complaints_db import insert_complaint
from nlp.processor import SmartElectricityComplaintAnalyzer

logger = logging.getLogger(__name__)

router = APIRouter()


class AnalyzeRequest(BaseModel):
    complaint: str = Field(..., description="Electricity complaint text")


class AnalyzeResponse(BaseModel):
    issue_type: str
    location: str
    priority: str
    suggested_action: str


@lru_cache(maxsize=1)
def get_analyzer() -> SmartElectricityComplaintAnalyzer:
    # Loading spaCy model can be slow; cache a single instance.
    return SmartElectricityComplaintAnalyzer()


def build_suggested_action(issue_type: str, priority: str) -> str:
    issue_type = issue_type or "power_cut"
    priority = priority or "low"

    if issue_type == "power_cut":
        if priority == "high":
            return "Report outage; keep the main switch off; avoid operating electrical devices; contact the utility emergency/support line."
        return "Check neighbors/area outage status; avoid using high-power appliances until power stabilizes; report the issue to the utility."

    if issue_type == "billing_issue":
        return "Verify bill details and meter reading; keep payment/reference documents; file a billing dispute/complaint with the utility."

    if issue_type == "transformer_fault":
        if priority == "high":
            return "Stay away from the transformer area; do not touch poles/wiring; switch off nearby circuits only if safe; report to utility immediately."
        return "Avoid the affected area; note any visible damage/smoke; report the transformer fault to the utility."

    if issue_type == "voltage_issue":
        if priority == "high":
            return "Reduce appliance usage; avoid sensitive electronics; if safe, switch off affected circuits; report unstable voltage immediately."
        return "Limit appliance usage during fluctuations; report voltage instability to the utility."

    return "Report the complaint to the utility; include relevant details and observations."


def map_pipeline_output(pipeline_result: Dict[str, Any]) -> AnalyzeResponse:
    try:
        issue_type = pipeline_result["issue_classification"]["issue_type"]
        matched_keywords = pipeline_result["issue_classification"]["matched_keywords"]
        location = pipeline_result["entity_extraction"]["location"]
        priority = pipeline_result["urgency"]["level"]
    except KeyError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected NLP output shape: missing {exc}",
        ) from exc

    suggested_action = build_suggested_action(issue_type=issue_type, priority=priority)
    # Keep internal classifier detection available if needed,
    # but do not expose it in the API response.
    _classifier_label = "Keyword Fallback"
    if isinstance(matched_keywords, list) and matched_keywords:
        first_match = str(matched_keywords[0]).lower()
        if first_match.startswith("ai:"):
            _classifier_label = "AI Model"

    return AnalyzeResponse(
        issue_type=str(issue_type),
        location=str(location),
        priority=str(priority),
        suggested_action=suggested_action,
    )


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    complaint = request.complaint or ""
    if not complaint.strip():
        raise HTTPException(status_code=400, detail="`complaint` must be a non-empty string.")

    try:
        analyzer = get_analyzer()
        pipeline_result = analyzer.analyze(complaint)
        response = map_pipeline_output(pipeline_result)

        # Persist the analysis for later retrieval.
        insert_complaint(
            complaint=complaint,
            issue=response.issue_type,
            location=response.location,
            priority=response.priority,
        )

        return response
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to analyze complaint")
        raise HTTPException(status_code=500, detail="Failed to analyze complaint.") from exc

