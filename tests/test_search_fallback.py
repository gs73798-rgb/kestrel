from unittest.mock import patch

from kestrel import FakeModelClient, Kestrel, SessionStore, WorkspaceContext
from kestrel.tools import MAX_FALLBACK_SEARCH_BYTES


def build_agent(tmp_path):
    (tmp_path / "README.md").write_text("needle here\n", encoding="utf-8")
    store = SessionStore(tmp_path / ".kestrel" / "sessions")
    return Kestrel(
        model_client=FakeModelClient([]),
        workspace=WorkspaceContext.build(tmp_path),
        session_store=store,
        approval_policy="auto",
    )


def test_fallback_search_skips_ignored_dirs_binary_and_oversized_files(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("needle\n", encoding="utf-8")
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "lib.py").write_text("needle\n", encoding="utf-8")
    (tmp_path / "blob.bin").write_bytes(b"needle\0\1\2")
    (tmp_path / "huge.txt").write_text("needle\n" + "x" * MAX_FALLBACK_SEARCH_BYTES, encoding="utf-8")
    agent = build_agent(tmp_path)

    # 强制走回退分支：模拟机器上没有 rg。
    with patch("kestrel.tools.shutil.which", return_value=None):
        result = agent.run_tool("search", {"pattern": "needle", "path": "."})

    assert "README.md:1:needle here" in result
    assert ".git" not in result
    assert ".venv" not in result
    assert "blob.bin" not in result
    assert "huge.txt" not in result
