"""Fork: the server only reads, only reaches configured NAS units, and checks Access."""

import asyncio
from unittest.mock import patch

import pytest
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

import mcp_server
from config import SynologyConfig
from readonly import READ_ONLY_API_METHODS, READ_ONLY_TOOLS
from utils.synology_api import SynologyAPIClient


@pytest.fixture
def server():
    return mcp_server.SynologyMCPServer()


def test_only_read_only_tools_are_listed(server):
    tools = server._get_tool_definitions()
    assert {tool.name for tool in tools} == READ_ONLY_TOOLS
    for tool in tools:
        assert tool.annotations.read_only_hint is True
        assert tool.annotations.destructive_hint is False
        assert "base_url" not in tool.input_schema.get("properties", {})


def test_write_tools_are_unknown(server):
    for name in ("delete", "synology_create_user", "synology_container_stop", "synology_login"):
        with pytest.raises(ValueError, match="Unknown tool"):
            asyncio.run(server._dispatch_tool(name, {}))


def test_base_url_is_refused(server):
    with pytest.raises(Exception, match="base_url is not accepted"):
        server._get_base_url({"base_url": "https://attacker.example"})


def test_client_refuses_calls_outside_the_allowlist():
    client = SynologyAPIClient("https://nas", "sid")
    with patch("utils.synology_api.requests") as requests:
        result = client.post("SYNO.Core.User", "create", 1, {"name": "x"})
        stream = client.post_stream("SYNO.Docker.Project", "start_stream", 1, {"id": "x"})
    assert result["error"]["code"] == "read_only"
    assert stream["error"]["code"] == "read_only"
    requests.get.assert_not_called()
    requests.post.assert_not_called()


def test_every_listed_tool_only_sends_allowlisted_calls(server):
    """Run each tool against a fake DSM: nothing it sends may be refused."""
    sent = []

    def fake_request(self, api, method, version=1, extra_params=None, use_post=False, timeout=None):
        sent.append((api, method))
        return {"success": True, "data": {}}

    server.sessions["https://nas"] = "sid"
    server.nas_name_map["nas"] = "https://nas"
    sample = {"disk_id": "sata1", "name": "x", "target_id": 1, "uuid_or_description": "x"}
    with patch.object(SynologyAPIClient, "_do_request", fake_request):
        for name in READ_ONLY_TOOLS:
            tool, handler = server._tool_registry[name]
            declared = tool.input_schema.get("properties", {})
            arguments = {"nas_name": "nas", **{k: v for k, v in sample.items() if k in declared}}
            try:
                asyncio.run(handler(arguments))
            except mcp_server.ToolFailureError:
                pass  # empty fake data, e.g. "no LUN named x"
    assert sent
    assert set(sent) <= READ_ONLY_API_METHODS


def test_nas_units_come_from_the_environment(monkeypatch):
    monkeypatch.setenv("SYNOLOGY_NAS_NAMES", "nas1, nas2")
    monkeypatch.setenv("SYNOLOGY_NAS1_URL", "https://192.0.2.10:8465/")
    monkeypatch.setenv("SYNOLOGY_NAS1_USERNAME", "mcp")
    monkeypatch.setenv("SYNOLOGY_NAS1_PASSWORD", "secret")
    monkeypatch.setenv("SYNOLOGY_NAS1_VERIFY_SSL", "false")
    monkeypatch.setenv("SYNOLOGY_NAS2_URL", "https://192.0.2.20:8465")
    monkeypatch.setenv("SYNOLOGY_NAS2_USERNAME", "mcp")
    monkeypatch.delenv("SYNOLOGY_NAS2_PASSWORD", raising=False)

    cfg = SynologyConfig()

    assert cfg.get_nas_names() == ["nas1"]  # nas2 has no password
    nas = cfg.get_synology_config("nas1")
    assert nas["base_url"] == "https://192.0.2.10:8465"
    assert nas["username"] == "mcp"
    assert nas["password"] == "secret"
    assert nas["verify_ssl"] is False


def _app():
    async def ok(request):
        return PlainTextResponse("ok")

    return Starlette(routes=[Route("/mcp", ok, methods=["POST"]), Route("/healthz", ok)])


def test_http_requires_the_access_jwt(monkeypatch):
    monkeypatch.setenv("CF_ACCESS_TEAM_DOMAIN", "team.cloudflareaccess.com")
    monkeypatch.setenv("CF_ACCESS_AUD", "aud")
    client = TestClient(mcp_server.access_protected(_app()))

    assert client.get("/healthz").status_code == 200
    assert client.post("/mcp").status_code == 403
    assert client.post("/mcp", headers={"Cf-Access-Jwt-Assertion": "not-a-jwt"}).status_code == 403


def test_http_refuses_to_start_without_access_settings(monkeypatch):
    for name in ("CF_ACCESS_TEAM_DOMAIN", "CF_ACCESS_AUD", "ALLOW_WITHOUT_ACCESS_JWT"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(Exception, match="CF_ACCESS_TEAM_DOMAIN"):
        mcp_server.access_protected(_app())
