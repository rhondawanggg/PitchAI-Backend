# File: backend/app/models/project.py

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class ProjectStatus(str, Enum):
    PENDING_REVIEW = "pending_review"  # Score 60-79: 待评审
    PROCESSING = "processing"          # No score yet: 处理中
    COMPLETED = "completed"            # Score ≥80: 已完成
    FAILED = "failed"                  # Score <60: 未通过


class ReviewResult(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    CONDITIONAL = "conditional"


class ProjectBase(BaseModel):
    enterprise_name: str = Field(..., min_length=1, max_length=255)
    project_name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    team_members: Optional[str] = Field(None, max_length=1000)  # NEW: Team members field


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    enterprise_name: Optional[str] = Field(None, min_length=1, max_length=255)
    project_name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    team_members: Optional[str] = Field(None, max_length=1000)  # NEW: Team members field
    status: Optional[ProjectStatus] = None
    review_result: Optional[ReviewResult] = None


class ProjectInDB(ProjectBase):
    id: str
    status: ProjectStatus = ProjectStatus.PROCESSING
    total_score: Optional[float] = None
    review_result: Optional[ReviewResult] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    def get_status_display(self) -> str:
        """Get user-friendly status display text"""
        status_map = {
            ProjectStatus.PENDING_REVIEW: "待评审",
            ProjectStatus.PROCESSING: "处理中",
            ProjectStatus.COMPLETED: "已完成",
            ProjectStatus.FAILED: "未通过"
        }
        return status_map.get(self.status, "未知")

    def get_status_category(self) -> str:
        """Get status category for grouping"""
        if self.status == ProjectStatus.COMPLETED:
            return "excellent"  # ≥80分
        elif self.status == ProjectStatus.PENDING_REVIEW:
            return "good"       # 60-79分
        elif self.status == ProjectStatus.FAILED:
            return "poor"       # <60分
        else:
            return "processing" # 处理中

    def get_team_members_display(self) -> str:
        """Get team members with fallback"""
        return self.team_members or "团队信息待补充"


class ProjectList(BaseModel):
    total: int
    items: List[ProjectInDB]


class ProjectStatistics(BaseModel):
    pending_review: int      # 60-79分: 待评审
    completed: int           # ≥80分: 已完成
    failed: int              # <60分: 未通过
    processing: int          # 无评分: 处理中
    needs_info: int = 0      # DEPRECATED: For backward compatibility
    recent_projects: List[ProjectInDB]


class ProjectDetail(ProjectInDB):
    """Extended project information for detail views"""
    pass


# Query parameters for listing projects
class ProjectListParams(BaseModel):
    page: int = Field(1, ge=1, le=1000)
    size: int = Field(10, ge=1, le=100)
    status: Optional[ProjectStatus] = None
    search: Optional[str] = Field(None, max_length=255)

    class Config:
        extra = "forbid"


def calculate_status_from_score(total_score: Optional[float]) -> ProjectStatus:
    """Calculate project status based on total score"""
    if total_score is None:
        return ProjectStatus.PROCESSING
    elif total_score >= 80:
        return ProjectStatus.COMPLETED
    elif total_score >= 60:
        return ProjectStatus.PENDING_REVIEW
    else:
        return ProjectStatus.FAILED


def calculate_review_result_from_score(total_score: Optional[float]) -> Optional[ReviewResult]:
    """Calculate review result based on total score"""
    if total_score is None:
        return None
    elif total_score >= 80:
        return ReviewResult.PASS
    elif total_score >= 60:
        return ReviewResult.CONDITIONAL
    else:
        return ReviewResult.FAIL