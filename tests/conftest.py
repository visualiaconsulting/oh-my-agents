import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def temp_project():
    """Create a temporary project directory with .opencode/agents/ structure."""
    tmp = tempfile.mkdtemp()
    root = Path(tmp)
    agent_dir = root / ".opencode" / "agents"
    agent_dir.mkdir(parents=True)

    agent_data = {
        "orchestrator.md": """---
name: orchestrator
description: Central system orchestrator
mode: primary
model: opencode-go/deepseek-v4-pro
temperature: 0.2
permission:
  edit: deny
  bash: allow
  read: allow
  task: allow
---

Central system orchestrator.
""",
        "python-engineer.md": """---
name: python-engineer
description: Senior software engineer
mode: subagent
model: opencode-go/deepseek-v4-flash
temperature: 0.2
permission:
  edit: allow
  bash: allow
  read: allow
  task: deny
---

Senior software engineer.
""",
    }

    for name, content in agent_data.items():
        (agent_dir / name).write_text(content, encoding="utf-8")

    # Create context.md for plan detection
    (root / ".opencode" / "context.md").write_text("""---
project: test
plan: go
version: 1.0
---
""", encoding="utf-8")

    yield root
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def temp_empty_project():
    """Temporary directory without agents."""
    tmp = tempfile.mkdtemp()
    root = Path(tmp)
    yield root
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def clean_env():
    """Remove OpenCode-related env vars for plan detection tests."""
    saved = {}
    for key in ("OPENCODE_PLAN", "ANTHROPIC_API_KEY", "GITHUB_TOKEN",
                "COPILOT_TOKEN", "OPENROUTER_API_KEY", "OLLAMA_HOST"):
        saved[key] = os.environ.pop(key, None)
    yield
    for key, val in saved.items():
        if val is not None:
            os.environ[key] = val
        elif key in os.environ:
            del os.environ[key]


@pytest.fixture
def mock_questionary():
    """Mock questionary to avoid interactive prompts."""
    with patch("questionary.confirm") as mock_confirm, \
         patch("questionary.select") as mock_select, \
         patch("questionary.text") as mock_text:
        mock_confirm.return_value.ask.return_value = True
        mock_select.return_value.ask.return_value = "default"
        mock_text.return_value.ask.return_value = "test-agent"
        yield {
            "confirm": mock_confirm,
            "select": mock_select,
            "text": mock_text,
        }
