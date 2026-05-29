"""
AMRShield - API Schemas
Pydantic models for request/response validation.
"""

from pydantic import BaseModel, Field
from typing import Optional


class PatientCase(BaseModel):
    """Input schema for /recommend endpoint."""
    patient_id: str = Field(default="ANON-001", description="Anonymized patient ID — no real PHI")
    age: int = Field(..., ge=0, le=120, description="Age in years")
    sex: str = Field(..., pattern="^(male|female)$", description="Biological sex")
    weight: float = Field(..., gt=0, le=300, description="Weight in kg")
    serum_creatinine: float = Field(..., gt=0, description="Serum creatinine in mg/dL")
    diagnosis: str = Field(..., description="Clinical diagnosis")
    infection_site: str = Field(..., description="Site of infection")
    suspected_pathogen: str = Field(default="Unknown (empirical)")
    allergies: list[str] = Field(default_factory=list)
    current_medications: list[str] = Field(default_factory=list)
    culture_results: Optional[dict] = Field(default=None)

    class Config:
        json_schema_extra = {
            "example": {
                "patient_id": "SYNTH-001",
                "age": 65,
                "sex": "female",
                "weight": 58.0,
                "serum_creatinine": 1.4,
                "diagnosis": "Urinary Tract Infection",
                "infection_site": "UTI",
                "suspected_pathogen": "E. coli",
                "allergies": ["penicillin"],
                "current_medications": ["warfarin", "metformin"],
                "culture_results": {},
            }
        }


class PredictRequest(BaseModel):
    """Input schema for /predict endpoint."""
    country: str = Field(..., description="Country name for WHO GLASS lookup")
    pathogen: str = Field(..., description="Pathogen to forecast resistance for")
    antibiotic: Optional[str] = Field(default=None, description="Specific antibiotic to forecast")
    horizon_months: int = Field(default=6, ge=1, le=24, description="Forecast horizon in months")

    class Config:
        json_schema_extra = {
            "example": {
                "country": "India",
                "pathogen": "E. coli",
                "antibiotic": "ciprofloxacin",
                "horizon_months": 6,
            }
        }


class AuditResponse(BaseModel):
    """Output schema for audit results."""
    audit_id: str
    trace_id: str
    overall_result: str  # PASS | FLAG | HOLD
    issues_found: list[dict]
    severity_level: str
    recommendation_safe_to_proceed: bool
    physician_review_required: bool
    audit_reasoning: str
