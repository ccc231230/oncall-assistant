import re
from pathlib import Path
from fastapi import UploadFile
from app.core.config import settings
from app.core.html_parser import parse_html

DATA_DIR = Path(settings.DATA_DIR).resolve()


def _validate_filename(fname: str) -> str:
    """Sanitize and validate filename. Returns sanitized path or raises ValueError."""
    sanitized = re.sub(r'[/\\]', '', fname)
    sanitized = sanitized.replace('..', '')
    sanitized = sanitized.strip()
    if not sanitized:
        raise ValueError("empty filename")
    filepath = (DATA_DIR / sanitized).resolve()
    filepath.relative_to(DATA_DIR)  # raises ValueError if path traversal
    return filepath


def read_file(fname: str) -> str:
    """
    Read an SOP HTML file from the data directory.
    Security: prevents path traversal by stripping directory components and validating the resolved path.
    """
    try:
        filepath = _validate_filename(fname)
    except ValueError as e:
        return f"Error: {str(e)}"

    # Check file exists
    if not filepath.exists():
        available = [f.name for f in DATA_DIR.glob("*.html")]
        return f"Error: file '{fname}' not found. Available files: {', '.join(available)}"

    if not filepath.is_file():
        return f"Error: '{fname}' is not a file"

    # Read and parse
    try:
        html = filepath.read_text(encoding="utf-8")
        parsed = parse_html(html)
        return f"# {parsed['title']}\n\n{parsed['content']}"
    except Exception as e:
        return f"Error reading file '{fname}': {str(e)}"


def save_uploaded_file(file: UploadFile) -> dict:
    """
    Save an uploaded file to DATA_DIR.
    Security: validates filename, prevents path traversal, restricts to .html files.
    Returns dict with success/filename/size/error.
    """
    if not file.filename:
        return {"success": False, "error": "文件名不能为空"}

    # Validate extension
    if not file.filename.lower().endswith(".html"):
        return {"success": False, "error": "只允许上传 .html 文件"}

    try:
        filepath = _validate_filename(file.filename)
    except ValueError as e:
        return {"success": False, "error": f"文件名非法: {str(e)}"}

    # Read content
    try:
        content = file.file.read()
    except Exception:
        return {"success": False, "error": "读取文件失败"}

    # Size check
    max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content) > max_size:
        return {
            "success": False,
            "error": f"文件过大，最大允许 {settings.MAX_UPLOAD_SIZE_MB}MB",
        }

    # Write to disk
    try:
        filepath.write_bytes(content)
        return {"success": True, "filename": file.filename, "size": len(content)}
    except Exception as e:
        return {"success": False, "error": f"写入文件失败: {str(e)}"}
