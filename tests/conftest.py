import pytest
import tempfile
import os

@pytest.fixture
def tmp_hermes_home(tmp_path):
    """Create a temp HERMES_HOME for testing."""
    os.environ["HERMES_HOME"] = str(tmp_path)
    (tmp_path / "config.yaml").write_text("")
    (tmp_path / "skills").mkdir()
    (tmp_path / "cron").mkdir()
    (tmp_path / "memories").mkdir()
    yield tmp_path
    del os.environ["HERMES_HOME"]