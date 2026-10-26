import subprocess
import sys
from pathlib import Path

import mini_kestrel


def test_mini_kestrel_module_and_public_exports():
    assert mini_kestrel.Kestrel is not None
    assert mini_kestrel.FakeModelClient is not None
    assert not hasattr(mini_kestrel, "MiniAgent")
    result = subprocess.run([sys.executable, "-m", "mini_kestrel", "--help"], capture_output=True, text=True, check=True)
    assert "Teaching-sized Kestrel agent harness" in result.stdout


def test_readme_main_mapping_points_to_existing_files():
    repo_root = Path(__file__).resolve().parents[3]
    main_files = [
        "kestrel/cli.py",
        "kestrel/runtime.py",
        "kestrel/agent_loop.py",
        "kestrel/context_manager.py",
        "kestrel/providers/clients.py",
        "kestrel/tool_executor.py",
        "kestrel/tools.py",
        "kestrel/task_state.py",
        "kestrel/run_store.py",
        "kestrel/workspace.py",
    ]
    for path in main_files:
        assert (repo_root / path).exists()
