# File: backend/app/models/score.py

from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime


class SubDimensionScore(BaseModel):
    sub_dimension: str = Field(..., min_length=1, max_length=100)
    score: float = Field(..., ge=0)
    max_score: float = Field(..., gt=0)
    comments: Optional[str] = None

    @validator('score')
    def score_not_exceed_max(cls, v, values):
        if 'max_score' in values and v > values['max_score']:
            raise ValueError('score cannot exceed max_score')
        return v


class DimensionScore(BaseModel):
    dimension: str = Field(..., min_length=1, max_length=100)
    score: float = Field(..., ge=0)
    max_score: float = Field(..., gt=0)
    comments: Optional[str] = None
    sub_dimensions: List[SubDimensionScore] = []

    @validator('score')
    def score_not_exceed_max(cls, v, values):
        if 'max_score' in values and v > values['max_score']:
            raise ValueError('score cannot exceed max_score')
        return v


class ProjectScores(BaseModel):
    dimensions: List[DimensionScore]


class ProjectScoresInDB(ProjectScores):
    project_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ScoreUpdate(BaseModel):
    dimensions: List[DimensionScore]

    @validator('dimensions')
    def validate_unique_dimensions(cls, v):
        dimension_names = [dim.dimension for dim in v]
        if len(dimension_names) != len(set(dimension_names)):
            raise ValueError('duplicate dimension names not allowed')
        return v


class MissingInformation(BaseModel):
    id: Optional[str] = None  # ID for existing records, None for new ones
    dimension: str
    information_type: str
    description: str
    status: str = "pending"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class MissingInformationList(BaseModel):
    items: List[MissingInformation]


# Standard scoring dimensions with default max scores
STANDARD_DIMENSIONS = {
    "团队能力": {
        "max_score": 30,
        "sub_dimensions": {
            "核心团队背景": 10,
            "团队完整性": 10,
            "团队执行力": 10
        }
    },
    "产品&技术": {
        "max_score": 20,
        "sub_dimensions": {
            "技术创新性": 8,
            "产品成熟度": 6,
            "研发能力": 6
        }
    },
    "市场前景": {
        "max_score": 20,
        "sub_dimensions": {
            "市场空间": 8,
            "竞争分析": 6,
            "市场策略": 6
        }
    },
    "商业模式": {
        "max_score": 20,
        "sub_dimensions": {
            "盈利模式": 8,
            "运营模式": 6,
            "发展模式": 6
        }
    },
    "财务情况": {
        "max_score": 10,
        "sub_dimensions": {
            "财务状况": 5,
            "融资需求": 5
        }
    }
}