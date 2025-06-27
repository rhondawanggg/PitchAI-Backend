# File: backend/app/models/business_plan.py

from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
from enum import Enum


class BusinessPlanStatus(str, Enum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class BusinessPlanBase(BaseModel):
    project_id: str
    file_name: str
    file_size: int
    status: BusinessPlanStatus = BusinessPlanStatus.PROCESSING


class BusinessPlanCreate(BusinessPlanBase):
    """For creating new business plans - no datetime fields to avoid serialization issues"""
    pass


class BusinessPlanUpdate(BaseModel):
    status: Optional[BusinessPlanStatus] = None
    error_message: Optional[str] = None


class BusinessPlanInDB(BusinessPlanBase):
    id: str
    upload_time: datetime
    updated_at: datetime
    error_message: Optional[str] = None

    class Config:
        from_attributes = True
        # Enable JSON serialization of datetime objects
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    @validator('upload_time', 'updated_at', pre=True)
    def parse_datetime(cls, v):
        if isinstance(v, str):
            # Handle timezone suffixes
            if v.endswith('Z'):
                v = v.replace('Z', '+00:00')
            return datetime.fromisoformat(v)
        return v


# Helper functions for database operations
def create_business_plan_data(project_id: str, file_name: str, file_size: int) -> dict:
    """Create data dict for database insertion with proper datetime handling"""
    current_time = datetime.utcnow().isoformat()
    return {
        "project_id": project_id,
        "file_name": file_name,
        "file_size": file_size,
        "status": BusinessPlanStatus.PROCESSING.value,
        "upload_time": current_time,
        "updated_at": current_time
    }


def update_business_plan_data(status: BusinessPlanStatus, error_message: Optional[str] = None) -> dict:
    """Create update data dict with proper datetime handling"""
    data = {
        "status": status.value,
        "updated_at": datetime.utcnow().isoformat()
    }
    if error_message:
        data["error_message"] = error_message
    return data