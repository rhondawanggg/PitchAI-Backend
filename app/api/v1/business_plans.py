# File: backend/app/api/v1/business_plans.py

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from typing import List
import uuid
import os
from datetime import datetime
from ...models.business_plan import (
    BusinessPlanCreate,
    BusinessPlanInDB,
    BusinessPlanStatus,
)
from ...services.storage import storage_service
from ...services.document.processor import document_processor
from ...services.evaluation.deepseek_client import deepseek_client
from ...core.database import db
from ...models.project import calculate_status_from_score, calculate_review_result_from_score

router = APIRouter()


async def process_and_evaluate_bp(bp_id: str, project_id: str, file_path: str):
    """Background task to process document and run evaluation"""
    supabase = db.get_client()

    try:
        print(f"🔄 Starting background processing for BP {bp_id}")

        # Step 1: Extract text from PDF
        print("📄 Extracting text from PDF...")
        document_text = await document_processor.extract_text_from_pdf(file_path)

        if len(document_text.strip()) < 50:
            raise ValueError("Document text too short or extraction failed")

        # Step 2: Run AI evaluation
        print("🤖 Running AI evaluation...")
        evaluation_result = await deepseek_client.evaluate_business_plan(document_text)

        # Step 3: Store evaluation results in scores tables
        print("💾 Storing evaluation results...")
        await store_evaluation_results(project_id, evaluation_result)

        # Step 4: Update business plan status
        supabase.table("business_plans").update({
            "status": BusinessPlanStatus.COMPLETED.value,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", bp_id).execute()

        # UPDATED Step 5: Project status will be automatically updated by database trigger
        # based on total_score, so we don't need to set it manually here
        print(f"✅ Successfully processed BP {bp_id}")

    except Exception as e:
        print(f"❌ Background processing failed for BP {bp_id}: {str(e)}")

        # Update status to completed but mark as needing manual review
        supabase.table("business_plans").update({
            "status": BusinessPlanStatus.COMPLETED.value,
            "error_message": f"AI处理失败: {str(e)}",
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", bp_id).execute()

        # UPDATED: Set project status to failed if AI evaluation fails
        supabase.table("projects").update({
            "status": "failed",  # UPDATED: Use failed status for evaluation failures
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", project_id).execute()

        # Add missing information record to trigger manual review
        supabase.table("missing_information").insert({
            "id": str(uuid.uuid4()),
            "project_id": project_id,
            "dimension": "AI评估",
            "information_type": "自动评估失败",
            "description": f"AI自动评估失败: {str(e)}，请进行人工评审",
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }).execute()


async def store_evaluation_results(project_id: str, evaluation_result: dict):
    """Store evaluation results in the scores and score_details tables"""
    supabase = db.get_client()

    try:
        # First, delete any existing scores for this project
        existing_scores = supabase.table("scores").select("id").eq("project_id", project_id).execute()

        for score_row in existing_scores.data:
            # Delete sub-dimensions first
            supabase.table("score_details").delete().eq("score_id", score_row['id']).execute()

        # Delete main dimension scores
        supabase.table("scores").delete().eq("project_id", project_id).execute()

        # Store new evaluation results
        dimensions = evaluation_result.get("dimensions", {})

        for dimension_name, dimension_data in dimensions.items():
            # Insert main dimension score
            score_id = str(uuid.uuid4())

            score_data = {
                "id": score_id,
                "project_id": project_id,
                "dimension": dimension_name,
                "score": dimension_data.get("score", 0),
                "max_score": dimension_data.get("max_score", 0),
                "comments": dimension_data.get("comments", ""),
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }

            supabase.table("scores").insert(score_data).execute()

            # Insert sub-dimension scores
            sub_dimensions = dimension_data.get("sub_dimensions", [])
            for sub_dim in sub_dimensions:
                sub_score_data = {
                    "id": str(uuid.uuid4()),
                    "score_id": score_id,
                    "sub_dimension": sub_dim.get("sub_dimension", ""),
                    "score": sub_dim.get("score", 0),
                    "max_score": sub_dim.get("max_score", 0),
                    "comments": sub_dim.get("comments", ""),
                    "created_at": datetime.utcnow().isoformat()
                }

                supabase.table("score_details").insert(sub_score_data).execute()

        # Store missing information
        missing_info = evaluation_result.get("missing_information", [])
        for missing_item in missing_info:
            missing_data = {
                "id": str(uuid.uuid4()),
                "project_id": project_id,
                "dimension": missing_item.get("type", "其他"),
                "information_type": missing_item.get("type", "其他"),
                "description": missing_item.get("description", ""),
                "status": "pending",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }

            supabase.table("missing_information").insert(missing_data).execute()

        # ✅ NEW: Save AI evaluation to history after storing current scores
        await save_ai_evaluation_to_history(project_id, evaluation_result)

        print(f"✅ Successfully stored evaluation results for project {project_id}")

    except Exception as e:
        print(f"❌ Failed to store evaluation results: {str(e)}")
        raise

async def save_ai_evaluation_to_history(project_id: str, evaluation_result: dict):
    """Save AI evaluation results to review history"""
    supabase = db.get_client()

    try:
        # Build the dimensions structure for history
        dimensions = {}
        evaluation_dimensions = evaluation_result.get("dimensions", {})

        for dimension_name, dimension_data in evaluation_dimensions.items():
            # Convert sub_dimensions list to the expected format
            sub_dimensions = []
            for sub_dim in dimension_data.get("sub_dimensions", []):
                sub_dimensions.append({
                    "sub_dimension": sub_dim.get("sub_dimension", ""),
                    "score": float(sub_dim.get("score", 0)),
                    "max_score": float(sub_dim.get("max_score", 0)),
                    "comments": sub_dim.get("comments", "")
                })

            dimensions[dimension_name] = {
                "score": float(dimension_data.get("score", 0)),
                "max_score": float(dimension_data.get("max_score", 0)),
                "comments": dimension_data.get("comments", ""),
                "sub_dimensions": sub_dimensions
            }

        # Calculate total score
        total_score = evaluation_result.get("total_score", 0)

        # Create history record for AI evaluation
        history_data = {
            "id": str(uuid.uuid4()),
            "project_id": project_id,
            "total_score": float(total_score),
            "dimensions": dimensions,
            "modified_by": "AI系统",
            "modification_notes": f"DeepSeek AI自动评估 (总分: {total_score}/100)",
            "created_at": datetime.utcnow().isoformat()
        }

        result = supabase.table("review_history").insert(history_data).execute()

        if result.data:
            print(f"✅ Saved AI evaluation to history for project {project_id}")
        else:
            print(f"⚠️ Failed to save AI evaluation to history")

    except Exception as e:
        print(f"⚠️ Failed to save AI evaluation to history: {str(e)}")
        # Don't fail the main operation if history save fails

@router.post("/projects/{project_id}/business-plans", response_model=BusinessPlanInDB)
async def upload_business_plan(
    project_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """Upload business plan and trigger background processing - FIXED VERSION"""

    # FIXED: Basic validations first, before touching the file
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="只支持PDF文件")

    # FIXED: Validate UUID format early
    try:
        uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID format")

    # FIXED: Check if project exists early
    supabase = db.get_client()
    project_result = supabase.table("projects").select("id").eq("id", project_id).execute()
    if not project_result.data:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        # FIXED: Save file first, then validate - avoid file pointer corruption
        print(f"💾 Saving file for project {project_id}")
        file_path, filename = await storage_service.save_business_plan(file, project_id)

        # FIXED: Get file size from saved file, not from UploadFile
        file_size = storage_service.get_file_size(file_path)

        # FIXED: Validate file size after saving
        if file_size > 20 * 1024 * 1024:  # 20MB limit
            storage_service.delete_file(file_path)
            raise HTTPException(status_code=400, detail="文件大小不能超过20MB")

        if file_size == 0:
            storage_service.delete_file(file_path)
            raise HTTPException(status_code=400, detail="文件为空或保存失败")

        # FIXED: Validate the saved PDF file
        print(f"🔍 Validating PDF file: {file_path}")
        if not document_processor.validate_pdf_file(file_path):
            storage_service.delete_file(file_path)
            raise HTTPException(status_code=400, detail="Invalid PDF file or corrupted")

        # FIXED: Create BP record in database
        bp_id = str(uuid.uuid4())
        current_time = datetime.utcnow().isoformat()

        bp_data = {
            "id": bp_id,
            "project_id": project_id,
            "file_name": filename,
            "file_size": file_size,
            "status": BusinessPlanStatus.PROCESSING.value,
            "upload_time": current_time,
            "updated_at": current_time
        }

        print(f"💾 Saving BP record to database: {bp_id}")
        result = supabase.table("business_plans").insert(bp_data).execute()

        if not result.data:
            storage_service.delete_file(file_path)
            raise HTTPException(status_code=500, detail="保存BP记录失败")

        # Update project status to processing
        supabase.table("projects").update({
            "status": "processing",
            "updated_at": current_time
        }).eq("id", project_id).execute()

        print(f"✅ BP upload successful, starting background processing")

        # Add background task for processing and evaluation
        background_tasks.add_task(
            process_and_evaluate_bp,
            bp_id,
            project_id,
            file_path
        )

        # Return success response immediately
        return BusinessPlanInDB(
            id=bp_id,
            project_id=project_id,
            file_name=filename,
            file_size=file_size,
            status=BusinessPlanStatus.PROCESSING,
            upload_time=datetime.fromisoformat(current_time),
            updated_at=datetime.fromisoformat(current_time)
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        print(f"❌ Upload failed with error: {str(e)}")
        # Clean up any partial files
        if 'file_path' in locals():
            storage_service.delete_file(file_path)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/projects/{project_id}/business-plans/status", response_model=BusinessPlanInDB)
async def get_business_plan_status(project_id: str):
    """Get BP processing status - FIXED VERSION"""
    supabase = db.get_client()

    try:
        # Validate UUID format
        try:
            uuid.UUID(project_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid project ID format")

        print(f"🔍 Getting BP status for project: {project_id}")
        result = (
            supabase.table("business_plans")
            .select("*")
            .eq("project_id", project_id)
            .order("upload_time", desc=True)
            .limit(1)
            .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="未找到BP记录")

        # Convert database row to model - FIXED datetime handling
        row = result.data[0]
        print(f"✅ Found BP record: {row['id']} with status: {row['status']}")

        return BusinessPlanInDB(
            id=row['id'],
            project_id=row['project_id'],
            file_name=row['file_name'],
            file_size=row['file_size'],
            status=BusinessPlanStatus(row['status']),
            upload_time=datetime.fromisoformat(row['upload_time'].replace('Z', '+00:00')) if isinstance(row['upload_time'], str) else row['upload_time'],
            updated_at=datetime.fromisoformat(row['updated_at'].replace('Z', '+00:00')) if isinstance(row['updated_at'], str) else row['updated_at'],
            error_message=row.get('error_message')
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Failed to get BP status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get BP status: {str(e)}")


@router.get("/projects/{project_id}/business-plans/download")
async def download_business_plan(project_id: str):
    """Download the business plan PDF for a project"""
    supabase = db.get_client()

    try:
        # Validate UUID format
        try:
            uuid.UUID(project_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid project ID format")

        # Get the business plan record from database
        result = (
            supabase.table("business_plans")
            .select("*")
            .eq("project_id", project_id)
            .order("upload_time", desc=True)
            .limit(1)
            .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="No business plan found for this project")

        bp_record = result.data[0]

        # Construct the file path
        file_name = bp_record['file_name']
        file_path = os.path.join(storage_service.bp_dir, file_name)

        # Check if file exists
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=404,
                detail=f"Business plan file not found on disk: {file_name}"
            )

        # Get original filename (remove timestamp prefix)
        original_filename = file_name.split('_', 2)[-1] if '_' in file_name else file_name

        # Return the file
        return FileResponse(
            path=file_path,
            media_type='application/pdf',
            filename=original_filename,
            headers={
                "Content-Disposition": f"attachment; filename=\"{original_filename}\""
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download business plan: {str(e)}")


@router.get("/projects/{project_id}/business-plans/info")
async def get_business_plan_info(project_id: str):
    """Get business plan information without downloading the file - ENHANCED DEBUG VERSION"""
    supabase = db.get_client()

    try:
        # Validate UUID format
        try:
            uuid.UUID(project_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid project ID format")

        print(f"🔍 Getting BP info for project: {project_id}")

        # Get the business plan record
        result = (
            supabase.table("business_plans")
            .select("*")
            .eq("project_id", project_id)
            .order("upload_time", desc=True)
            .limit(1)
            .execute()
        )

        print(f"📊 Database query result: {len(result.data)} records found")

        if not result.data:
            print(f"❌ No BP record found in database for project: {project_id}")
            # ENHANCED: Let's also check if there are ANY BP records to debug
            all_bps = supabase.table("business_plans").select("project_id, id, file_name").execute()
            print(f"📊 Total BP records in database: {len(all_bps.data)}")
            for bp in all_bps.data[:5]:  # Show first 5 for debugging
                print(f"   - Project: {bp['project_id']}, File: {bp['file_name']}")
            raise HTTPException(status_code=404, detail="No business plan found for this project")

        bp_record = result.data[0]
        print(f"✅ Found BP record: {bp_record['id']} for project: {project_id}")

        # Check if file exists on disk
        file_path = os.path.join(storage_service.bp_dir, bp_record['file_name'])
        file_exists = os.path.exists(file_path)

        print(f"📁 File path: {file_path}")
        print(f"📄 File exists on disk: {file_exists}")

        # Get original filename (remove timestamp prefix)
        original_filename = bp_record['file_name'].split('_', 2)[-1] if '_' in bp_record['file_name'] else bp_record['file_name']

        response_data = {
            "id": bp_record['id'],
            "project_id": bp_record['project_id'],
            "file_name": original_filename,
            "file_size": bp_record['file_size'],
            "status": bp_record['status'],
            "upload_time": bp_record['upload_time'],
            "file_exists": file_exists,
            "download_url": f"/api/v1/projects/{project_id}/business-plans/download" if file_exists else None,
            # DEBUG INFO
            "debug_info": {
                "stored_filename": bp_record['file_name'],
                "file_path": file_path,
                "storage_dir": str(storage_service.bp_dir)
            }
        }

        print(f"✅ Returning BP info: {response_data}")
        return response_data

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Failed to get business plan info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get business plan info: {str(e)}")


@router.post("/projects/{project_id}/business-plans/reprocess")
async def reprocess_business_plan(project_id: str, background_tasks: BackgroundTasks):
    """Reprocess an existing business plan (re-run AI evaluation)"""
    supabase = db.get_client()

    try:
        # Validate UUID format
        try:
            uuid.UUID(project_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid project ID format")

        # Get the business plan record
        result = (
            supabase.table("business_plans")
            .select("*")
            .eq("project_id", project_id)
            .order("upload_time", desc=True)
            .limit(1)
            .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="No business plan found for this project")

        bp_record = result.data[0]
        file_path = os.path.join(storage_service.bp_dir, bp_record['file_name'])

        # Check if file exists
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Business plan file not found on disk")

        # Update status to processing
        supabase.table("business_plans").update({
            "status": BusinessPlanStatus.PROCESSING.value,
            "error_message": None,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", bp_record['id']).execute()

        # Update project status
        supabase.table("projects").update({
            "status": "processing",
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", project_id).execute()

        # Add background task for reprocessing
        background_tasks.add_task(
            process_and_evaluate_bp,
            bp_record['id'],
            project_id,
            file_path
        )

        return {"message": "Business plan reprocessing started"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reprocess business plan: {str(e)}")