import os
import shutil
from datetime import datetime
from fastapi import UploadFile
from typing import Tuple
from pathlib import Path
import uuid


class StorageService:
    def __init__(self):
        # FIXED: Use absolute path and ensure directory exists
        self.base_dir = Path(__file__).parent.parent.parent  # Go up to backend root
        self.upload_dir = self.base_dir / "uploads"
        self.bp_dir = self.upload_dir / "business_plans"
        self._ensure_directories()

    def _ensure_directories(self):
        """确保必要的目录存在"""
        try:
            self.upload_dir.mkdir(parents=True, exist_ok=True)
            self.bp_dir.mkdir(parents=True, exist_ok=True)
            print(f"✅ Storage directories created: {self.bp_dir}")
        except Exception as e:
            print(f"❌ Failed to create storage directories: {e}")
            raise

    async def save_business_plan(
        self, file: UploadFile, project_id: str
    ) -> Tuple[str, str]:
        """
        保存商业计划书文件
        返回: (文件路径, 文件名)
        """
        try:
            # FIXED: Generate safe filename with UUID to avoid conflicts
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_uuid = str(uuid.uuid4())[:8]

            # Sanitize original filename
            original_name = file.filename or "business_plan.pdf"
            safe_name = "".join(c for c in original_name if c.isalnum() or c in "._-")

            filename = f"{project_id}_{timestamp}_{file_uuid}_{safe_name}"
            file_path = self.bp_dir / filename

            print(f"💾 Saving file to: {file_path}")

            # FIXED: Reset file position to start and use async read
            await file.seek(0)
            content = await file.read()

            if not content:
                raise ValueError("Uploaded file is empty")

            # Save file content
            with open(file_path, "wb") as buffer:
                buffer.write(content)

            # Verify file was saved correctly
            if not file_path.exists():
                raise FileNotFoundError(f"File was not saved: {file_path}")

            file_size = file_path.stat().st_size
            if file_size == 0:
                raise ValueError(f"Saved file is empty: {file_path}")

            print(f"✅ File saved successfully: {filename} ({file_size} bytes)")
            return str(file_path), filename

        except Exception as e:
            print(f"❌ Failed to save business plan: {e}")
            # Clean up partial file if it exists
            try:
                if 'file_path' in locals() and file_path.exists():
                    file_path.unlink()
            except:
                pass
            raise

    def get_file_size(self, file_path: str) -> int:
        """获取文件大小(字节)"""
        try:
            return Path(file_path).stat().st_size
        except Exception as e:
            print(f"❌ Failed to get file size for {file_path}: {e}")
            return 0

    def delete_file(self, file_path: str) -> bool:
        """删除文件"""
        try:
            Path(file_path).unlink(missing_ok=True)
            return True
        except Exception as e:
            print(f"❌ Failed to delete file {file_path}: {e}")
            return False

    def file_exists(self, file_path: str) -> bool:
        """检查文件是否存在"""
        return Path(file_path).exists()

    def get_file_url(self, file_path: str) -> str:
        """获取文件访问URL (未来可扩展为云存储URL)"""
        # For now, return relative path that could be served by FastAPI
        try:
            relative_path = Path(file_path).relative_to(self.base_dir)
            return f"/files/{relative_path}"
        except ValueError:
            return file_path


# Global instance
storage_service = StorageService()