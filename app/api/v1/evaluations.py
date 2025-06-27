from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from ...core.database import db

router = APIRouter()

@router.get("/projects/{project_id}/evaluation")
async def get_evaluation_results(project_id: str) -> Dict[str, Any]:
    """获取项目评估结果"""
    supabase = db.get_client()

    # Get evaluation results from database
    result = (
        supabase.table("evaluations")
        .select("*")
        .eq("project_id", project_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="评估结果未找到")

    return result.data[0]

async def save_evaluation_results(business_plan_id: str, evaluation: Dict[str, Any]):
    """保存评估结果到数据库"""
    supabase = db.get_client()

    # Save main evaluation record
    evaluation_record = {
        "business_plan_id": business_plan_id,
        "total_score": evaluation["total_score"],
        "evaluation_data": evaluation,
        "status": "completed"
    }

    result = supabase.table("evaluations").insert(evaluation_record).execute()
    return result.data[0] if result.data else None