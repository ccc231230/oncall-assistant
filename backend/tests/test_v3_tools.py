"""Tests for app.v3.tools.read_file — path traversal security is critical."""

import pytest
from unittest.mock import patch
from pathlib import Path

from app.v3.tools import read_file


@pytest.fixture
def real_data_dir():
    """真实 data/ 目录路径，用于测试正常读取。"""
    return Path(__file__).resolve().parent.parent.parent / "data"


class TestReadFileNormal:
    """Tests for normal file reading behavior."""

    def test_read_existing_file(self, real_data_dir):
        """正常读取 data/sop-001.html，返回非空字符串。"""
        with patch("app.v3.tools.settings") as mock_settings:
            mock_settings.DATA_DIR = str(real_data_dir)

            result = read_file("sop-001.html")

            assert len(result) > 0
            assert "# " in result  # Should contain markdown-style title
            assert "后端服务" in result or "SOP" in result

    def test_read_file_not_found(self, real_data_dir):
        """读取不存在的文件返回错误提示。"""
        with patch("app.v3.tools.settings") as mock_settings:
            mock_settings.DATA_DIR = str(real_data_dir)

            result = read_file("sop-999.html")

            assert "Error" in result
            assert "not found" in result or "sop-999" in result


class TestReadFileSecurity:
    """Security tests for path traversal prevention."""

    def test_unix_path_traversal_blocked(self, real_data_dir):
        """
        路径穿越防护：../../../etc/passwd 被拒绝。
        read_file 会移除所有 / 字符，因此 "../../../etc/passwd" 变成 "....etcpasswd"，
        然后 .. 被移除变成 "etcpasswd"，文件不存在 → 返回错误。
        """
        with patch("app.v3.tools.settings") as mock_settings:
            mock_settings.DATA_DIR = str(real_data_dir)

            result = read_file("../../../etc/passwd")

            # Must not read system files — should return an error
            assert "Error" in result or "access denied" in result.lower()
            assert "root:" not in result  # Definitely not leaking passwd

    @pytest.mark.skipif(
        "\\" not in str(Path.cwd()), reason="Backslash test only valid on Windows"
    )
    def test_windows_path_traversal_blocked(self, real_data_dir):
        """反斜杠路径穿越：..\\..\\ 被拒绝。"""
        with patch("app.v3.tools.settings") as mock_settings:
            mock_settings.DATA_DIR = str(real_data_dir)

            result = read_file("..\\..\\..\\Windows\\System32\\drivers\\etc\\hosts")

            assert "Error" in result or "access denied" in result.lower()

    def test_mixed_slashes_blocked(self, real_data_dir):
        """斜杠+点点组合：sop-001.html/../../etc/passwd 被拒绝。"""
        with patch("app.v3.tools.settings") as mock_settings:
            mock_settings.DATA_DIR = str(real_data_dir)

            result = read_file("sop-001.html/../../etc/passwd")

            assert "Error" in result or "access denied" in result.lower()

    def test_empty_filename(self, real_data_dir):
        """空文件名：返回错误提示。"""
        with patch("app.v3.tools.settings") as mock_settings:
            mock_settings.DATA_DIR = str(real_data_dir)

            result = read_file("")

            assert "Error" in result

    def test_only_dots(self, real_data_dir):
        """纯点点输入：被拒绝。"""
        with patch("app.v3.tools.settings") as mock_settings:
            mock_settings.DATA_DIR = str(real_data_dir)

            result = read_file("....")

            assert "Error" in result or "access denied" in result.lower()

    def test_absolute_path_blocked(self, real_data_dir):
        """绝对路径：/etc/passwd 被拒绝（斜杠被移除后变为 etcpasswd）。"""
        with patch("app.v3.tools.settings") as mock_settings:
            mock_settings.DATA_DIR = str(real_data_dir)

            result = read_file("/etc/passwd")

            # Slashes stripped, becomes "etcpasswd" — not found or denied
            assert "Error" in result or "access denied" in result.lower()
