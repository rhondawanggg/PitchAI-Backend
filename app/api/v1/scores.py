# File: backend/app/api/v1/scores.py

from fastapi import APIRouter, HTTPException
from typing import List
import uuid
from datetime import datetime
from ...models.score import (
    ProjectScores,
    ProjectScoresInDB,
    ScoreUpdate,
    DimensionScore,
    SubDimensionScore,
    MissingInformation,
    MissingInformationList,
    STANDARD_DIMENSIONS
)
from ...core.database import db

router = APIRouter()

async def save_score_history_after_update(project_id: str, new_scores: List[DimensionScore], modification_notes: str = None):
    """
    FIXED: Save NEW scores to history AFTER updating (consistent with AI evaluations)
    This replaces the old save_score_history function that saved OLD scores before updating
    """
    supabase = db.get_client()

    try:
        # Calculate total score from new scores
        total_score = sum(score.score for score in new_scores)

        # Build dimensions JSON structure from NEW scores
        dimensions = {}

        for score in new_scores:
            sub_dimensions = [
                {
                    "sub_dimension": sub.sub_dimension,
                    "score": float(sub.score),
                    "max_score": float(sub.max_score),
                    "comments": sub.comments or ""
                }
                for sub in score.sub_dimensions
            ]

            dimensions[score.dimension] = {
                "score": float(score.score),
                "max_score": float(score.max_score),
                "comments": score.comments or "",
                "sub_dimensions": sub_dimensions
            }

        # Save NEW scores to history
        history_data = {
            "id": str(uuid.uuid4()),
            "project_id": project_id,
            "total_score": float(total_score),
            "dimensions": dimensions,
            "modified_by": "manual_edit",  # Could be enhanced with actual user info
            "modification_notes": modification_notes or "手动评分修改",
            "created_at": datetime.utcnow().isoformat()
        }

        result = supabase.table("review_history").insert(history_data).execute()

        if result.data:
            print(f"✅ Saved NEW scores to history for project {project_id} (total: {total_score})")
        else:
            print(f"⚠️ Failed to save NEW scores to history")

    except Exception as e:
        print(f"⚠️ Failed to save NEW scores to history: {str(e)}")
        # Don't fail the main operation if history save fails


def row_to_dimension_score(score_row: dict, sub_dimensions: List[dict]) -> DimensionScore:
    """Convert database rows to DimensionScore model"""
    sub_dim_scores = [
        SubDimensionScore(
            sub_dimension=sub['sub_dimension'],
            score=float(sub['score']),
            max_score=float(sub['max_score']),
            comments=sub['comments']
        )
        for sub in sub_dimensions
    ]

    return DimensionScore(
        dimension=score_row['dimension'],
        score=float(score_row['score']),
        max_score=float(score_row['max_score']),
        comments=score_row['comments'],
        sub_dimensions=sub_dim_scores
    )


@router.get("/projects/{project_id}/scores", response_model=ProjectScores)
async def get_project_scores(project_id: str):
    """Get scores for a specific project"""
    supabase = db.get_client()

    try:
        # Validate UUID format
        try:
            uuid.UUID(project_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid project ID format")

        # Check if project exists
        project_result = supabase.table("projects").select("id").eq("id", project_id).execute()
        if not project_result.data:
            raise HTTPException(status_code=404, detail="Project not found")

        # Get dimension scores
        scores_result = supabase.table("scores").select("*").eq("project_id", project_id).execute()

        # Get sub-dimension scores for all scores
        dimensions = []
        for score_row in scores_result.data:
            # Get sub-dimensions for this score
            sub_dims_result = supabase.table("score_details").select("*").eq("score_id", score_row['id']).execute()

            dimension_score = row_to_dimension_score(score_row, sub_dims_result.data)
            dimensions.append(dimension_score)

        # If no scores exist, return default structure with zero scores
        if not dimensions:
            dimensions = []
            for dim_name, dim_config in STANDARD_DIMENSIONS.items():
                sub_dimensions = []
                for sub_name, sub_max in dim_config["sub_dimensions"].items():
                    sub_dimensions.append(SubDimensionScore(
                        sub_dimension=sub_name,
                        score=0,
                        max_score=sub_max,
                        comments=""
                    ))

                dimensions.append(DimensionScore(
                    dimension=dim_name,
                    score=0,
                    max_score=dim_config["max_score"],
                    comments="",
                    sub_dimensions=sub_dimensions
                ))

        return ProjectScores(dimensions=dimensions)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get scores: {str(e)}")


@router.put("/projects/{project_id}/scores", response_model=ProjectScores)
async def update_project_scores(project_id: str, score_update: ScoreUpdate):
    """
    FIXED: Update scores for a specific project with correct history logic
    """
    supabase = db.get_client()

    try:
        # Validate UUID format
        try:
            uuid.UUID(project_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid project ID format")

        # Check if project exists
        project_result = supabase.table("projects").select("id").eq("id", project_id).execute()
        if not project_result.data:
            raise HTTPException(status_code=404, detail="Project not found")

        print(f"📝 Updating scores for project {project_id}")
        print(f"📊 New scores: {[(d.dimension, d.score) for d in score_update.dimensions]}")

        # Begin transaction-like operations
        # First, delete existing scores and sub-scores for this project
        existing_scores = supabase.table("scores").select("id").eq("project_id", project_id).execute()

        for score_row in existing_scores.data:
            # Delete sub-dimensions first (due to foreign key constraints)
            supabase.table("score_details").delete().eq("score_id", score_row['id']).execute()

        # Delete main dimension scores
        supabase.table("scores").delete().eq("project_id", project_id).execute()

        # Insert NEW scores
        for dimension in score_update.dimensions:
            # Insert main dimension score
            score_id = str(uuid.uuid4())
            score_data = {
                "id": score_id,
                "project_id": project_id,
                "dimension": dimension.dimension,
                "score": dimension.score,
                "max_score": dimension.max_score,
                "comments": dimension.comments,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }

            result = supabase.table("scores").insert(score_data).execute()
            if not result.data:
                raise HTTPException(status_code=500, detail=f"Failed to insert score for {dimension.dimension}")

            # Insert sub-dimension scores
            for sub_dim in dimension.sub_dimensions:
                sub_score_data = {
                    "id": str(uuid.uuid4()),
                    "score_id": score_id,
                    "sub_dimension": sub_dim.sub_dimension,
                    "score": sub_dim.score,
                    "max_score": sub_dim.max_score,
                    "comments": sub_dim.comments,
                    "created_at": datetime.utcnow().isoformat()
                }

                sub_result = supabase.table("score_details").insert(sub_score_data).execute()
                if not sub_result.data:
                    print(f"⚠️ Failed to insert sub-score for {sub_dim.sub_dimension}")

        print(f"✅ Successfully inserted all NEW scores to database")

        # Update project status to completed if it has scores
        supabase.table("projects").update({
            "status": "completed",
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", project_id).execute()

        # ✅ FIXED: Save NEW scores to history AFTER successful update (consistent with AI evaluations)
        total_score = sum(d.score for d in score_update.dimensions)
        await save_score_history_after_update(
            project_id,
            score_update.dimensions,
            f"手动评分修改 (新总分: {total_score}/100)"
        )

        print(f"✅ Score update complete for project {project_id}")

        # Return updated scores
        return await get_project_scores(project_id)

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Failed to update scores: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update scores: {str(e)}")


@router.get("/projects/{project_id}/scores/history")
async def get_project_score_history(project_id: str):
    """Get score change history for a project"""
    supabase = db.get_client()

    try:
        # Validate UUID format
        try:
            uuid.UUID(project_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid project ID format")

        # Check if project exists
        project_result = supabase.table("projects").select("id, project_name, enterprise_name").eq("id", project_id).execute()
        if not project_result.data:
            raise HTTPException(status_code=404, detail="Project not found")

        project_info = project_result.data[0]

        # Get score history
        history_result = supabase.table("review_history").select("*").eq("project_id", project_id).order("created_at", desc=True).execute()

        history_items = []
        for record in history_result.data:
            history_items.append({
                "id": record["id"],
                "total_score": float(record["total_score"]),
                "modified_by": record["modified_by"],
                "modification_notes": record["modification_notes"],
                "created_at": record["created_at"],
                "dimensions": record["dimensions"]  # JSON object with full dimension details
            })

        return {
            "project_id": project_id,
            "project_name": project_info["project_name"],
            "enterprise_name": project_info["enterprise_name"],
            "history": history_items
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get score history: {str(e)}")


@router.get("/projects/{project_id}/missing-information", response_model=MissingInformationList)
async def get_missing_information(project_id: str):
    """Get missing information for a specific project - FIXED VERSION"""
    supabase = db.get_client()

    try:
        # Validate UUID format
        try:
            uuid.UUID(project_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid project ID format")

        # Check if project exists
        project_result = supabase.table("projects").select("id").eq("id", project_id).execute()
        if not project_result.data:
            raise HTTPException(status_code=404, detail="Project not found")

        # FIXED: Get missing information with IDs
        result = supabase.table("missing_information").select("*").eq("project_id", project_id).execute()

        missing_items = []
        for row in result.data:
            # FIXED: Use the updated model that includes ID and timestamps
            missing_item = MissingInformation(
                id=row['id'],
                dimension=row['dimension'],
                information_type=row['information_type'],
                description=row['description'],
                status=row['status'],
                created_at=row.get('created_at'),
                updated_at=row.get('updated_at')
            )
            missing_items.append(missing_item)

        return {"items": missing_items}

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Failed to get missing information: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get missing information: {str(e)}")


@router.post("/projects/{project_id}/missing-information")
async def add_missing_information(
    project_id: str,
    missing_info: MissingInformation
):
    """Add missing information record for a project - FIXED VERSION"""
    supabase = db.get_client()

    try:
        # Validate UUID format
        try:
            uuid.UUID(project_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid project ID format")

        # Check if project exists
        project_result = supabase.table("projects").select("id").eq("id", project_id).execute()
        if not project_result.data:
            raise HTTPException(status_code=404, detail="Project not found")

        # FIXED: Validate required fields
        if not missing_info.dimension or not missing_info.description:
            raise HTTPException(status_code=400, detail="Dimension and description are required")

        # FIXED: Prevent duplicate submissions by checking for exact matches
        existing_check = supabase.table("missing_information").select("id").eq("project_id", project_id).eq("dimension", missing_info.dimension).eq("description", missing_info.description).execute()

        if existing_check.data:
            raise HTTPException(status_code=409, detail="This missing information already exists")

        # Insert missing information record
        missing_data = {
            "id": str(uuid.uuid4()),
            "project_id": project_id,
            "dimension": missing_info.dimension,
            "information_type": missing_info.information_type or "",
            "description": missing_info.description,
            "status": missing_info.status or "pending",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }

        print(f"💾 Inserting missing info: {missing_data}")
        result = supabase.table("missing_information").insert(missing_data).execute()

        if not result.data:
            print(f"❌ Failed to insert missing info - no data returned")
            raise HTTPException(status_code=500, detail="Failed to add missing information")

        print(f"✅ Successfully added missing info: {result.data[0]['id']}")

        # DON'T change project status automatically - let user manage this
        return {
            "message": "Missing information added successfully",
            "id": result.data[0]['id']
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Failed to add missing information: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to add missing information: {str(e)}")


@router.delete("/projects/{project_id}/missing-information/{info_id}")
async def remove_missing_information(project_id: str, info_id: str):
    """Remove a missing information record - FIXED VERSION"""
    supabase = db.get_client()

    try:
        # Validate UUID formats
        try:
            uuid.UUID(project_id)
            uuid.UUID(info_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid ID format")

        print(f"🗑️ Attempting to delete missing info: {info_id} for project: {project_id}")

        # FIXED: Check if the record exists first
        existing = supabase.table("missing_information").select("id").eq("id", info_id).eq("project_id", project_id).execute()

        if not existing.data:
            print(f"❌ Missing info record not found: {info_id}")
            raise HTTPException(status_code=404, detail="Missing information record not found")

        # Delete the missing information record
        result = supabase.table("missing_information").delete().eq("id", info_id).eq("project_id", project_id).execute()

        if not result.data:
            print(f"❌ Failed to delete missing info record")
            raise HTTPException(status_code=500, detail="Failed to delete missing information record")

        print(f"✅ Successfully deleted missing info: {info_id}")
        return {
            "message": "Missing information removed successfully",
            "deleted_id": info_id
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Failed to remove missing information: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to remove missing information: {str(e)}")


@router.get("/projects/{project_id}/scores/summary")
async def get_project_score_summary(project_id: str):
    """Get a summary of project scores including total and breakdown"""
    supabase = db.get_client()

    try:
        # Validate UUID format
        try:
            uuid.UUID(project_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid project ID format")

        # Get project with total score
        project_result = supabase.table("projects").select("*").eq("id", project_id).execute()
        if not project_result.data:
            raise HTTPException(status_code=404, detail="Project not found")

        project = project_result.data[0]

        # Get dimension scores
        scores_result = supabase.table("scores").select("dimension, score, max_score").eq("project_id", project_id).execute()

        dimension_breakdown = {}
        total_possible = 0

        for score_row in scores_result.data:
            dimension_breakdown[score_row['dimension']] = {
                "score": float(score_row['score']),
                "max_score": float(score_row['max_score']),
                "percentage": round((float(score_row['score']) / float(score_row['max_score'])) * 100, 1)
            }
            total_possible += float(score_row['max_score'])

        # Calculate overall percentage
        current_total = float(project['total_score']) if project['total_score'] else 0
        overall_percentage = round((current_total / total_possible) * 100, 1) if total_possible > 0 else 0

        # Determine recommendation based on score
        recommendation = "不符合入孵条件"
        if current_total >= 80:
            recommendation = "优秀项目，可考虑给予企业工位"
        elif current_total >= 60:
            recommendation = "符合基本入孵条件，可注册在工研院"

        return {
            "project_id": project_id,
            "project_name": project['project_name'],
            "enterprise_name": project['enterprise_name'],
            "total_score": current_total,
            "total_possible": total_possible,
            "overall_percentage": overall_percentage,
            "recommendation": recommendation,
            "dimension_breakdown": dimension_breakdown,
            "last_updated": project['updated_at']
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get score summary: {str(e)}")

@router.put("/projects/{project_id}/missing-information/{info_id}")
async def update_missing_information(
    project_id: str,
    info_id: str,
    missing_info: MissingInformation
):
    """Update a missing information record"""
    supabase = db.get_client()

    try:
        # Validate UUID formats
        try:
            uuid.UUID(project_id)
            uuid.UUID(info_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid ID format")

        # Check if project exists
        project_result = supabase.table("projects").select("id").eq("id", project_id).execute()
        if not project_result.data:
            raise HTTPException(status_code=404, detail="Project not found")

        # Check if missing info record exists
        existing = supabase.table("missing_information").select("id").eq("id", info_id).eq("project_id", project_id).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Missing information record not found")

        # Update the missing information record
        update_data = {
            "dimension": missing_info.dimension,
            "information_type": missing_info.information_type,
            "description": missing_info.description,
            "status": missing_info.status,
            "updated_at": datetime.utcnow().isoformat()
        }

        result = supabase.table("missing_information").update(update_data).eq("id", info_id).execute()

        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to update missing information")

        return {"message": "Missing information updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update missing information: {str(e)}")


@router.patch("/projects/{project_id}/missing-information/{info_id}/status")
async def update_missing_info_status(
    project_id: str,
    info_id: str,
    status: str
):
    """Update status of a specific missing information record"""
    supabase = db.get_client()

    try:
        # Validate UUID formats
        try:
            uuid.UUID(project_id)
            uuid.UUID(info_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid ID format")

        # Validate status
        valid_statuses = ["pending", "provided", "resolved"]
        if status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")

        # Update the status
        result = supabase.table("missing_information").update({
            "status": status,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", info_id).eq("project_id", project_id).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Missing information record not found")

        return {"message": "Missing information status updated successfully", "status": status}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update missing information status: {str(e)}")


@router.get("/projects/{project_id}/missing-information/{info_id}")
async def get_missing_information_detail(project_id: str, info_id: str):
    """Get specific missing information record"""
    supabase = db.get_client()

    try:
        # Validate UUID formats
        try:
            uuid.UUID(project_id)
            uuid.UUID(info_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid ID format")

        # Get the missing information record
        result = supabase.table("missing_information").select("*").eq("id", info_id).eq("project_id", project_id).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Missing information record not found")

        row = result.data[0]
        return MissingInformation(
            id=row['id'],
            dimension=row['dimension'],
            information_type=row['information_type'],
            description=row['description'],
            status=row['status'],
            created_at=row.get('created_at'),
            updated_at=row.get('updated_at')
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get missing information: {str(e)}")