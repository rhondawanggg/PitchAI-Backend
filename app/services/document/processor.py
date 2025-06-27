# File: backend/app/services/document/processor.py

from typing import List
import os
from pathlib import Path
import PyPDF2
import re

class DocumentProcessor:
    def __init__(self):
        pass

    async def extract_text_from_pdf(self, file_path: str) -> str:
        """
        Extract text from PDF file using PyPDF2
        """
        try:
            file_path_obj = Path(file_path)

            # Check if file exists
            if not file_path_obj.exists():
                raise FileNotFoundError(f"PDF file not found: {file_path}")

            # Check file size
            file_size = file_path_obj.stat().st_size
            if file_size == 0:
                raise ValueError("PDF file is empty")

            # Check if it's actually a PDF (basic check)
            with open(file_path, 'rb') as f:
                header = f.read(8)
                if not header.startswith(b'%PDF'):
                    raise ValueError("File is not a valid PDF")

            print(f"📄 Extracting text from PDF: {file_path} ({file_size} bytes)")

            # Extract text using PyPDF2
            extracted_text = ""

            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)

                # Check if PDF is encrypted
                if pdf_reader.is_encrypted:
                    print("⚠️ PDF is encrypted, attempting to decrypt...")
                    try:
                        pdf_reader.decrypt("")  # Try empty password
                    except:
                        raise ValueError("PDF is password protected and cannot be read")

                # Extract text from all pages
                total_pages = len(pdf_reader.pages)
                print(f"📖 Processing {total_pages} pages...")

                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            extracted_text += f"\n--- 第{page_num + 1}页 ---\n"
                            extracted_text += page_text
                            extracted_text += "\n"
                    except Exception as e:
                        print(f"⚠️ Error extracting text from page {page_num + 1}: {str(e)}")
                        continue

            # Clean and process the extracted text
            cleaned_text = self._clean_extracted_text(extracted_text)

            if len(cleaned_text.strip()) < 100:
                print("⚠️ Very little text extracted, PDF might be image-based")
                return self._generate_fallback_text(file_path, file_size)

            print(f"✅ Successfully extracted {len(cleaned_text)} characters from PDF")
            return cleaned_text

        except Exception as e:
            print(f"❌ Failed to extract text from PDF: {str(e)}")
            # Return fallback text for evaluation
            return self._generate_fallback_text(file_path, file_size)

    def _clean_extracted_text(self, text: str) -> str:
        """Clean and normalize extracted text"""
        if not text:
            return ""

        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)

        # Remove page breaks and form feeds
        text = re.sub(r'[\f\r]', '\n', text)

        # Normalize line breaks
        text = re.sub(r'\n\s*\n', '\n\n', text)

        # Remove very short lines that are likely headers/footers
        lines = text.split('\n')
        cleaned_lines = []

        for line in lines:
            line = line.strip()
            # Keep lines that are substantial or contain Chinese characters
            if len(line) > 3 or any('\u4e00' <= char <= '\u9fff' for char in line):
                cleaned_lines.append(line)

        return '\n'.join(cleaned_lines).strip()

    def _generate_fallback_text(self, file_path: str, file_size: int) -> str:
        """Generate fallback text when extraction fails"""
        return f"""
商业计划书文档处理说明

文件路径: {file_path}
文件大小: {file_size} 字节
处理状态: 文本提取失败或内容不足

可能的原因:
1. PDF文件为图片格式，无法提取文字
2. PDF文件加密或损坏
3. 文件内容过少

建议处理方式:
1. 请确保PDF文件包含可选择的文字内容
2. 如果是扫描件，请提供文字版本的PDF
3. 检查PDF文件是否完整且未加密

注意: 由于无法提取文档内容，本次评估将需要人工审核。
请评审专家手动查看原始PDF文件进行评分。
"""

    def chunk_text(self, text: str, chunk_size: int = 4000, overlap: int = 200) -> List[str]:
        """Split text into manageable chunks for processing"""
        if not text:
            return []

        # Remove excessive whitespace first
        text = re.sub(r'\s+', ' ', text).strip()

        chunks = []
        text_length = len(text)

        if text_length <= chunk_size:
            return [text]

        start = 0
        while start < text_length:
            end = start + chunk_size

            if end > text_length:
                end = text_length

            # Try to break at sentence boundaries for Chinese text
            if end < text_length:
                # Look for sentence endings in Chinese (。！？) or English (.!?)
                for i in range(end, max(start + chunk_size - 200, start), -1):
                    if text[i] in '。！？.!?':
                        end = i + 1
                        break

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            if end == text_length:
                break

            # Set next start position with overlap
            start = max(end - overlap, start + 1)

        return chunks

    def validate_pdf_file(self, file_path: str) -> bool:
        """Validate if file is a proper PDF and can be read"""
        try:
            file_path_obj = Path(file_path)

            if not file_path_obj.exists():
                return False

            # Check file size
            if file_path_obj.stat().st_size == 0:
                return False

            # Basic PDF header check
            with open(file_path, 'rb') as f:
                header = f.read(8)
                if not header.startswith(b'%PDF'):
                    return False

            # Try to open with PyPDF2
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)

                # Check if we can access at least one page
                if len(pdf_reader.pages) == 0:
                    return False

                # Try to read first page
                try:
                    first_page = pdf_reader.pages[0]
                    _ = first_page.extract_text()
                    return True
                except:
                    return False

        except Exception as e:
            print(f"PDF validation error: {str(e)}")
            return False

    def get_document_info(self, file_path: str) -> dict:
        """Get metadata information from PDF document"""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)

                info = {
                    "page_count": len(pdf_reader.pages),
                    "encrypted": pdf_reader.is_encrypted,
                    "metadata": {}
                }

                # Extract metadata if available
                if pdf_reader.metadata:
                    metadata = pdf_reader.metadata
                    info["metadata"] = {
                        "title": metadata.get("/Title", ""),
                        "author": metadata.get("/Author", ""),
                        "subject": metadata.get("/Subject", ""),
                        "creator": metadata.get("/Creator", ""),
                        "producer": metadata.get("/Producer", ""),
                        "creation_date": str(metadata.get("/CreationDate", "")),
                        "modification_date": str(metadata.get("/ModDate", ""))
                    }

                return info

        except Exception as e:
            print(f"Error getting document info: {str(e)}")
            return {"error": str(e)}

# Global instance
document_processor = DocumentProcessor()