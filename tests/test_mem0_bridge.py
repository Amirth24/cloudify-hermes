import importlib
import pytest
from unittest.mock import MagicMock, patch
from cloudify_hermes.sync.mem0_bridge import Mem0Bridge, categorize_entry

def test_categorize_entry_user_profile():
    entry = {"content": "User: Data Engineer at GEOPITS", "type": "preference"}
    assert categorize_entry(entry) == "user_profile"

def test_categorize_entry_environment():
    entry = {"content": "Swarm cluster: kube-master at 192.168.0.90", "type": "entity"}
    assert categorize_entry(entry) == "environment"

def test_categorize_entry_pattern():
    entry = {"content": "GitHub auth workflow: gh auth switch", "type": "pattern"}
    assert categorize_entry(entry) == "patterns"

def test_categorize_entry_default():
    entry = {"content": "Some random fact", "type": "unknown"}
    assert categorize_entry(entry) == "shared"

@patch("cloudify_hermes.sync.mem0_bridge.Mem0Bridge._get_mem0_client")
def test_mem0_push_stores_by_category(mock_client_factory):
    mock_client = MagicMock()
    mock_client_factory.return_value = mock_client
    bridge = Mem0Bridge(
        ov_endpoint="http://localhost:8765",
        mem0_api_key="test-key",
        user_id="amirth",
        agent_id="hermes-laptop",
    )
    entries = [
        {"content": "User likes Python", "type": "preference"},
        {"content": "Server at 10.0.0.1", "type": "entity"},
    ]
    bridge.push_entries(entries)
    assert mock_client.add.call_count == 2
    # Check category metadata
    first_call = mock_client.add.call_args_list[0]
    assert first_call[1]["metadata"]["category"] == "user_profile"
    second_call = mock_client.add.call_args_list[1]
    assert second_call[1]["metadata"]["category"] == "environment"

@patch("cloudify_hermes.sync.mem0_bridge.Mem0Bridge._get_mem0_client")
def test_mem0_push_skips_empty_content(mock_client_factory):
    mock_client = MagicMock()
    mock_client_factory.return_value = mock_client
    bridge = Mem0Bridge(mem0_api_key="test-key", user_id="amirth", agent_id="hermes")
    entries = [{"content": "", "type": "preference"}]
    bridge.push_entries(entries)
    mock_client.add.assert_not_called()


@patch("cloudify_hermes.sync.mem0_bridge.Mem0Bridge._get_mem0_client")
def test_defaults_from_env(mock_client_factory, monkeypatch):
    """Mem0Bridge falls back to CloudifyEnv when ov_endpoint/agent_id not passed."""
    monkeypatch.setenv("CLOUDIFY_OV_ENDPOINT", "http://env-endpoint:9999")
    monkeypatch.setenv("CLOUDIFY_AGENT_ID", "env-agent")
    # Re-import so CloudifyEnv picks up the monkeypatched env vars
    import cloudify_hermes.env
    importlib.reload(cloudify_hermes.env)
    # Also reload mem0_bridge so its module-level _env picks up the new CloudifyEnv
    import cloudify_hermes.sync.mem0_bridge
    importlib.reload(cloudify_hermes.sync.mem0_bridge)
    Mem0Bridge = cloudify_hermes.sync.mem0_bridge.Mem0Bridge

    mock_client = MagicMock()
    mock_client_factory.return_value = mock_client
    bridge = Mem0Bridge(mem0_api_key="test-key", user_id="amirth")
    assert bridge.ov_endpoint == "http://env-endpoint:9999"
    assert bridge.agent_id == "env-agent"