"""Tests for update_manager.py — version check and update mechanism."""

from io import BytesIO
from unittest.mock import patch, MagicMock
from zipfile import ZipFile


class TestGetCurrentVersion:
    """Tests for get_current_version()."""

    def test_reads_version_file(self, tmp_path):
        version_file = tmp_path / "VERSION"
        version_file.write_text("1.2.3\n")
        with patch("update_manager.SYSTEM_ROOT", tmp_path):
            # Re-import so the patched SYSTEM_ROOT is used
            from update_manager import get_current_version
            assert get_current_version() == "1.2.3"

    def test_fallback_to_zero(self, tmp_path):
        with patch("update_manager.SYSTEM_ROOT", tmp_path):
            from update_manager import get_current_version
            assert get_current_version() == "0.0.0"


class TestVersionGreater:
    """Tests for _version_greater()."""

    def test_greater(self):
        from update_manager import _version_greater
        assert _version_greater("1.2.3", "1.2.2") is True

    def test_not_greater(self):
        from update_manager import _version_greater
        assert _version_greater("1.2.1", "1.2.2") is False

    def test_equal(self):
        from update_manager import _version_greater
        assert _version_greater("1.2.1", "1.2.1") is False

    def test_fallback_without_packaging(self):
        """The fallback tuple comparison works when packaging is unavailable."""
        import builtins
        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "packaging.version" or name == "packaging":
                raise ImportError(f"No module named '{name}'")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=fake_import):
            import importlib
            import update_manager
            importlib.reload(update_manager)
            result = update_manager._version_greater("2.0.0", "1.9.9")
            assert result is True
            result2 = update_manager._version_greater("1.0.0", "1.0.1")
            assert result2 is False


class TestCheckForUpdates:
    """Tests for check_for_updates()."""

    @patch("requests.get")
    @patch("update_manager.get_current_version", return_value="1.2.1")
    def test_update_available(self, mock_version, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"tag_name": "v1.2.2"}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        from update_manager import check_for_updates
        has_update, current, latest = check_for_updates()
        assert has_update is True
        assert current == "1.2.1"
        assert latest == "1.2.2"

    @patch("requests.get")
    @patch("update_manager.get_current_version", return_value="1.2.1")
    def test_no_update(self, mock_version, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"tag_name": "v1.2.1"}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        from update_manager import check_for_updates
        has_update, current, latest = check_for_updates()
        assert has_update is False

    @patch("requests.get", side_effect=Exception("network error"))
    @patch("update_manager.get_current_version", return_value="1.2.1")
    def test_network_failure_graceful(self, mock_version, mock_get):
        from update_manager import check_for_updates
        has_update, current, latest = check_for_updates()
        assert has_update is False
        assert current == "1.2.1"
        assert latest == "1.2.1"


class TestMergeOpencodeDir:
    """Tests for _merge_opencode_dir()."""

    def test_merge_copies_context_and_agents(self, tmp_path):
        from update_manager import _merge_opencode_dir

        source = tmp_path / "source_opencode"
        dest = tmp_path / "dest_opencode"

        # Create source files
        (source / "agents").mkdir(parents=True)
        (source / "agents" / "orchestrator.md").write_text("new agent")
        (source / "context.md").write_text("new context")

        # Create existing data that must be preserved
        (dest / "sessions").mkdir(parents=True)
        (dest / "sessions" / "old.json").write_text("old session")

        _merge_opencode_dir(source, dest)

        # Verify new files were copied
        assert (dest / "context.md").read_text() == "new context"
        assert (dest / "agents" / "orchestrator.md").read_text() == "new agent"
        # Verify existing files were preserved
        assert (dest / "sessions" / "old.json").exists()

    def test_existing_agent_collection_and_context_are_preserved(self, tmp_path):
        from update_manager import _merge_opencode_dir

        source = tmp_path / "source"
        dest = tmp_path / "dest"
        (source / "agents").mkdir(parents=True)
        (dest / "agents").mkdir(parents=True)
        (source / "agents" / "orchestrator.md").write_text("new framework rules")
        (source / "agents" / "writer.md").write_text("new role")
        (source / "context.md").write_text("new framework context")
        (dest / "agents" / "orchestrator.md").write_text("custom instructions")
        (dest / "agents" / "custom.md").write_text("custom agent")
        (dest / "context.md").write_text("project decisions")

        _merge_opencode_dir(source, dest)

        assert (dest / "agents" / "orchestrator.md").read_text() == "custom instructions"
        assert (dest / "agents" / "custom.md").read_text() == "custom agent"
        assert not (dest / "agents" / "writer.md").exists()
        assert (dest / "context.md").read_text() == "project decisions"


def test_release_update_preserves_native_configuration_and_runtime_data(tmp_path):
    from update_manager import run_update

    protected_files = {
        ".codex/config.toml": 'model = "my-custom-model"',
        ".codex/agents/custom.toml": 'name = "custom"',
        ".agents/skills/frontend-design/SKILL.md": "installed skill",
        ".oh-my-agents/backups/export-1/config.toml": "original config",
        ".oh-my-agents/active.json": '{"runtime": "codex"}',
        ".venv/pyvenv.cfg": "local environment",
        "AGENTS.md": "project instructions outside managed block",
        ".opencode/agents/orchestrator.md": "my instructions",
        ".opencode/context.md": "my decisions",
        ".opencode/sessions/session.json": "my session",
    }
    for name, content in protected_files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    archive = BytesIO()
    with ZipFile(archive, "w") as zf:
        for name in protected_files:
            zf.writestr("oh-my-agents-9.0.0/" + name, "release default")
        zf.writestr("oh-my-agents-9.0.0/.codex/agents/writer.toml", "new framework agent")
        zf.writestr("oh-my-agents-9.0.0/.opencode/agents/writer.md", "new framework agent")
        zf.writestr("oh-my-agents-9.0.0/main.py", "# updated source\n")
        zf.writestr("oh-my-agents-9.0.0/VERSION", "9.0.0\n")
    response = MagicMock()
    response.iter_content.return_value = [archive.getvalue()]

    with patch("update_manager.SYSTEM_ROOT", tmp_path), patch("requests.get", return_value=response):
        ok, message = run_update("9.0.0")

    assert ok, message
    assert "--export --dry-run" in message
    for name, content in protected_files.items():
        assert (tmp_path / name).read_text(encoding="utf-8") == content
    assert not (tmp_path / ".codex/agents/writer.toml").exists()
    assert not (tmp_path / ".opencode/agents/writer.md").exists()
    assert (tmp_path / "main.py").read_text() == "# updated source\n"
    assert (tmp_path / "VERSION").read_text().strip() == "9.0.0"
