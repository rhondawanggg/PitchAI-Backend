# File: backend/app/api/v1/projects.py

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
import uuid
from datetime import datetime
from ...models.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectInDB,
    ProjectList,
    ProjectStatistics,
    ProjectDetail,
    ProjectListParams,
    ProjectStatus,
    calculate_status_from_score,
    calculate_review_result_from_score
)
from ...core.database import db
from pydantic import BaseModel

router = APIRouter()


# Helper function to convert database row to model
def row_to_project(row: dict) -> ProjectInDB:
    return ProjectInDB(
        id=row['id'],
        enterprise_name=row['enterprise_name'],
        project_name=row['project_name'],
        description=row['description'],
        team_members=row.get('team_members'),  # NEW: Handle team_members field
        status=ProjectStatus(row['status']),
        total_score=float(row['total_score']) if row['total_score'] else None,
        review_result=row['review_result'],
        created_at=row['created_at'],
        updated_at=row['updated_at']
    )


@router.get("/projects/statistics", response_model=ProjectStatistics)
async def get_project_statistics():
    """Get project statistics for dashboard with new status categories"""
    supabase = db.get_client()

    try:
        # Get counts by new status categories
        pending_result = supabase.table("projects").select("id", count="exact").eq("status", "pending_review").execute()
        completed_result = supabase.table("projects").select("id", count="exact").eq("status", "completed").execute()
        failed_result = supabase.table("projects").select("id", count="exact").eq("status", "failed").execute()
        processing_result = supabase.table("projects").select("id", count="exact").eq("status", "processing").execute()

        # Get recent projects (last 10)
        recent_result = supabase.table("projects").select("*").order("created_at", desc=True).limit(10).execute()

        recent_projects = [row_to_project(row) for row in recent_result.data]

        return ProjectStatistics(
            pending_review=pending_result.count or 0,    # 60-79分: 待评审
            completed=completed_result.count or 0,       # ≥80分: 已完成
            failed=failed_result.count or 0,            # <60分: 未通过
            processing=processing_result.count or 0,    # 无评分: 处理中
            needs_info=0,                               # DEPRECATED: Always 0 for compatibility
            recent_projects=recent_projects
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")


@router.get("/projects", response_model=ProjectList)
async def list_projects(
    page: int = Query(1, ge=1, le=1000),
    size: int = Query(100, ge=1, le=1000),  # INCREASED DEFAULT AND MAX SIZE FOR DASHBOARD
    status: Optional[ProjectStatus] = Query(None),
    search: Optional[str] = Query(None, max_length=255)
):
    """List projects with pagination, filtering, and search - UPDATED FOR DASHBOARD"""
    supabase = db.get_client()

    try:
        # Build query
        query = supabase.table("projects").select("*", count="exact")

        # Apply filters
        if status:
            query = query.eq("status", status.value)

        if search:
            # Search in both enterprise_name and project_name
            query = query.or_(f"enterprise_name.ilike.%{search}%,project_name.ilike.%{search}%")

        # Get total count first
        count_result = query.execute()
        total = count_result.count or 0

        # Apply pagination and get data
        offset = (page - 1) * size
        data_result = query.order("created_at", desc=True).range(offset, offset + size - 1).execute()

        items = [row_to_project(row) for row in data_result.data]

        return ProjectList(total=total, items=items)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list projects: {str(e)}")


@router.post("/projects", response_model=ProjectInDB)
async def create_project(project: ProjectCreate):
    """Create a new project"""
    supabase = db.get_client()

    try:
        # Generate UUID for the project
        project_id = str(uuid.uuid4())

        # Prepare data for insertion
        project_data = {
            "id": project_id,
            "enterprise_name": project.enterprise_name,
            "project_name": project.project_name,
            "description": project.description,
            "team_members": project.team_members,  # NEW: Include team_members
            "status": ProjectStatus.PROCESSING.value,  # Start as processing
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

        # Insert into database
        result = supabase.table("projects").insert(project_data).execute()

        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create project")

        return row_to_project(result.data[0])

    except Exception as e:
        if "duplicate key" in str(e).lower():
            raise HTTPException(status_code=409, detail="Project with this name already exists")
        raise HTTPException(status_code=500, detail=f"Failed to create project: {str(e)}")


@router.get("/projects/{project_id}", response_model=ProjectDetail)
async def get_project_detail(project_id: str):
    """Get detailed project information"""
    supabase = db.get_client()

    try:
        # Validate UUID format
        try:
            uuid.UUID(project_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid project ID format")

        # Get project details
        result = supabase.table("projects").select("*").eq("id", project_id).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Project not found")

        return row_to_project(result.data[0])

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get project: {str(e)}")


@router.put("/projects/{project_id}", response_model=ProjectInDB)
async def update_project(project_id: str, update_data: ProjectUpdate):
    """Update project information including team members"""
    supabase = db.get_client()

    try:
        # Validate UUID format
        try:
            uuid.UUID(project_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid project ID format")

        # Check if project exists
        existing = supabase.table("projects").select("id").eq("id", project_id).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Project not found")

        # Prepare update data (only include non-None fields)
        update_dict = {}
        for field, value in update_data.dict().items():
            if value is not None:
                if hasattr(value, 'value'):  # Handle Enum types
                    update_dict[field] = value.value
                else:
                    update_dict[field] = value

        if not update_dict:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        update_dict["updated_at"] = datetime.utcnow().isoformat()

        # Update project
        result = supabase.table("projects").update(update_dict).eq("id", project_id).execute()

        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to update project")

        return row_to_project(result.data[0])

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update project: {str(e)}")


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    """Delete a project"""
    supabase = db.get_client()

    try:
        # Validate UUID format
        try:
            uuid.UUID(project_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid project ID format")

        # Check if project exists
        existing = supabase.table("projects").select("id").eq("id", project_id).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Project not found")

        # Delete project (cascading deletes will handle related records)
        result = supabase.table("projects").delete().eq("id", project_id).execute()

        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to delete project")

        return {"message": "Project deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete project: {str(e)}")

class TeamMembersUpdate(BaseModel):
    team_members: str

@router.put("/projects/{project_id}/team-members")
async def update_team_members(project_id: str, update_data: TeamMembersUpdate):
    """Update only team members for a project - FIXED VERSION"""
    supabase = db.get_client()

    try:
        # Validate UUID format
        try:
            uuid.UUID(project_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid project ID format")

        # Check if project exists
        existing = supabase.table("projects").select("id").eq("id", project_id).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Project not found")

        # FIXED: Get team_members from request body object
        team_members = update_data.team_members

        # Validate team members length
        if len(team_members) > 1000:
            raise HTTPException(status_code=400, detail="Team members text too long (max 1000 characters)")

        print(f"💾 Updating team members for project {project_id}: {team_members[:50]}...")

        # Update team members
        result = supabase.table("projects").update({
            "team_members": team_members,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", project_id).execute()

        if not result.data:
            print(f"❌ Failed to update team members - no data returned")
            raise HTTPException(status_code=500, detail="Failed to update team members")

        print(f"✅ Successfully updated team members for project {project_id}")

        return {
            "message": "Team members updated successfully",
            "team_members": team_members
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Failed to update team members: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update team members: {str(e)}")