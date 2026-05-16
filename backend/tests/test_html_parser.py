"""Tests for app.core.html_parser.parse_html."""

from app.core.html_parser import parse_html


class TestParseHtml:
    """Tests for parse_html function."""

    def test_basic_parsing(self, sample_html_basic):
        """正常 HTML 解析：正确提取 title 和 content。"""
        result = parse_html(sample_html_basic)

        assert result["title"] == "后端服务 On-Call SOP"
        assert "后端服务值班工程师" in result["content"]
        assert "第一道防线" in result["content"]

    def test_script_tag_filtered(self, sample_html_with_script):
        """
        script 标签过滤：<script>replication</script> 的内容不应出现在 content 中。
        README 验证用例要求搜索 replication 返回空结果。
        """
        result = parse_html(sample_html_with_script)

        assert "replication" not in result["content"].lower()
        assert "replicationLag" not in result["content"]
        assert "checkReplication" not in result["content"]
        # Normal content should still be present
        assert "normal content about database" in result["content"]
        assert "More content here" in result["content"]

    def test_style_tag_filtered(self, sample_html_with_style):
        """style 标签过滤：CSS 内容不应出现在 content 中。"""
        result = parse_html(sample_html_with_style)

        assert "font-family" not in result["content"]
        assert "#ff0000" not in result["content"]
        assert "Arial" not in result["content"]
        # Normal content should still be present
        assert "Content without style pollution" in result["content"]

    def test_html_entities_decoded(self, sample_html_entities):
        """
        HTML entities 解码：&amp; → &，&#45; → -。
        BeautifulSoup 的 get_text() 会自动解码所有标准实体。
        """
        result = parse_html(sample_html_entities)

        # Title should have decoded entities
        assert "&" in result["title"]
        assert "-" in result["title"]
        # Content should have decoded entities
        assert "CDN & cache" in result["content"]

    def test_fallback_title_from_h1(self, sample_html_no_title):
        """无 <title> 时 fallback 到 <h1>。"""
        result = parse_html(sample_html_no_title)

        assert result["title"] == "Fallback Title from H1"
        assert "Content text" in result["content"]

    def test_whitespace_handling(self):
        """空白清理：多个连续换行应被合并。"""
        html = """<!DOCTYPE html>
<html>
<head><title>  Whitespace  Test  </title></head>
<body>
    <p>Line  one.</p>


    <p>Line  two.</p>
</body>
</html>"""
        result = parse_html(html)

        # Title should be stripped
        assert result["title"] == "Whitespace  Test"
        # Content should not have excessive blank lines
        assert "Line  one." in result["content"]
        assert "Line  two." in result["content"]
        # Verify content doesn't contain script/style artifacts
        lines = [l for l in result["content"].split("\n") if l.strip()]
        assert len(lines) == 2

    def test_empty_html(self):
        """空 HTML 输入：应返回默认 title。"""
        result = parse_html("<html></html>")
        assert result["title"] == "Untitled"
        assert result["content"] == ""

    def test_no_body_tag(self):
        """HTML 没有 <body> 标签时，fallback 到全文提取。"""
        html = """<!DOCTYPE html>
<html>
<head><title>No Body Test</title></head>
<p>Content without body wrapper.</p>
</html>"""
        result = parse_html(html)
        assert result["title"] == "No Body Test"
        assert "Content without body wrapper" in result["content"]
