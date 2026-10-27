class TestMCPConfig:
    def test_load_default_config(self, tmp_path):
        from mcp_config import MCPConfig
        config = MCPConfig(project_root=tmp_path)
        data = config.load()
        assert data["servers"] == []
        assert data["auto_connect"] is False

    def test_add_and_remove_server(self, tmp_path):
        from mcp_config import MCPConfig
        config = MCPConfig(project_root=tmp_path)
        config.add_server({"name": "test", "command": ["echo", "hello"]})
        assert len(config.get_servers()) == 1
        assert config.remove_server("test") is True
        assert len(config.get_servers()) == 0

    def test_get_template(self):
        from mcp_config import MCPConfig
        config = MCPConfig()
        template = config.get_template("filesystem")
        assert template is not None
        assert template["name"] == "filesystem"


class TestMCPServerConnection:
    def test_not_connected_initially(self):
        from mcp_client import MCPServerConnection
        conn = MCPServerConnection("test", {"command": ["echo"]})
        assert conn.is_connected is False

    def test_tools_empty_when_not_connected(self):
        from mcp_client import MCPServerConnection
        conn = MCPServerConnection("test", {"command": ["echo"]})
        assert conn.tools == []


class TestMCPClient:
    def test_no_tools_without_servers(self):
        from mcp_client import MCPClient
        client = MCPClient()
        assert client.get_all_tools() == []

    def test_inject_mcp_context_empty(self):
        from mcp_client import MCPClient
        client = MCPClient()
        assert client.inject_mcp_context() == ""


class TestSkillRecommender:
    def test_empty_project_no_recommendations(self, tmp_path):
        from skill_recommender import SkillRecommender
        rec = SkillRecommender(project_root=tmp_path)
        # tmp_path has no files matching triggers
        assert rec.get_recommendations() == []

    def test_detects_python_testing(self, tmp_path):
        from skill_recommender import SkillRecommender
        # Create a conftest.py to trigger python-testing
        (tmp_path / "conftest.py").write_text("# pytest config")
        rec = SkillRecommender(project_root=tmp_path)
        ids = [s["id"] for s in rec.get_recommendations()]
        assert "python-testing" in ids

    def test_generate_report(self, tmp_path):
        from skill_recommender import SkillRecommender
        (tmp_path / "Dockerfile").write_text("FROM python:3.11")
        rec = SkillRecommender(project_root=tmp_path)
        report = rec.generate_report()
        assert "docker" in report.lower() or "Recommended Skills" in report
