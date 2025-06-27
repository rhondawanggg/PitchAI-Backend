from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class SubDimensionScore(BaseModel):
    name: str
    score: float
    max_score: float
    comments: str

class DimensionScore(BaseModel):
    score: float
    max_score: float
    comments: str
    sub_dimensions: List[SubDimensionScore]

class MissingInformation(BaseModel):
    type: str
    description: str

class EvaluationResult(BaseModel):
    business_plan_id: str
    total_score: float
    dimensions: Dict[str, DimensionScore]
    missing_information: List[MissingInformation]
    status: str
    created_at: datetime

class EvaluationInDB(EvaluationResult):
    id: str
    updated_at: datetime