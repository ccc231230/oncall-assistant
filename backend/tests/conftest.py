import sys
from pathlib import Path

import pytest

# Ensure backend/ is on sys.path so "from app.xxx" imports work
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture
def sample_html_basic():
    """A minimal valid SOP HTML with no script/style tags."""
    return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>后端服务 On-Call SOP</title>
</head>
<body>
    <header>
        <h1>后端服务 On-Call SOP</h1>
    </header>
    <main>
        <h2>一、值班职责</h2>
        <p>后端服务值班工程师是保障线上服务稳定运行的第一道防线。</p>
    </main>
</body>
</html>"""


@pytest.fixture
def sample_html_with_script():
    """SOP HTML with script tag that should be decomposed."""
    return """<!DOCTYPE html>
<html>
<head><title>Test SOP</title></head>
<body>
    <h1>Test SOP</h1>
    <p>This is normal content about database.</p>
    <script>
        var replicationLag = 30;
        function checkReplication() {
            console.log("replication check");
        }
    </script>
    <p>More content here.</p>
</body>
</html>"""


@pytest.fixture
def sample_html_with_style():
    """SOP HTML with style tag that should be decomposed."""
    return """<!DOCTYPE html>
<html>
<head>
    <title>Styled SOP</title>
    <style>
        body { font-family: Arial; color: red; }
        .alert { background: #ff0000; }
    </style>
</head>
<body>
    <h1>Styled SOP</h1>
    <p>Content without style pollution.</p>
</body>
</html>"""


@pytest.fixture
def sample_html_entities():
    """SOP HTML with HTML entities that should be decoded."""
    return """<!DOCTYPE html>
<html>
<head><title>SOP&#45;003 &amp; Guide</title></head>
<body>
    <h1>SOP&#45;003 &amp; Guide</h1>
    <p>Use CDN &amp; cache for performance.</p>
</body>
</html>"""


@pytest.fixture
def sample_html_no_title():
    """SOP HTML without <title> tag, only <h1>."""
    return """<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body>
    <h1>Fallback Title from H1</h1>
    <p>Content text.</p>
</body>
</html>"""


@pytest.fixture
def data_dir():
    """Path to the real data/ directory for integration-style tests."""
    return Path(__file__).resolve().parent.parent.parent / "data"
