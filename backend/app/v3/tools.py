import re
from pathlib import Path
from app.core.config import settings
from app.core.html_parser import parse_html


def read_file(fname: str) -> str:
    """
    Read an SOP HTML file from the data directory.
    Security: prevents path traversal by stripping directory components and validating the resolved path.
    """
    DATA_DIR = Path(settings.DATA_DIR).resolve()

    # Sanitize: extract only the filename, strip all path separators and traversal
    sanitized = re.sub(r'[/\\]', '', fname)
    sanitized = sanitized.replace('..', '')
    sanitized = sanitized.strip()

    if not sanitized:
        return "Error: empty filename"

    # Resolve full path
    filepath = (DATA_DIR / sanitized).resolve()

    # Security: verify the resolved path is within DATA_DIR
    try:
        filepath.relative_to(DATA_DIR)
    except ValueError:
        return f"Error: access denied - path traversal attempt detected for '{fname}'"

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
