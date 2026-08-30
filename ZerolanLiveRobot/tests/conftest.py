import pytest


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests (no external dependencies)")
    config.addinivalue_line("markers", "integration: Integration tests (require live services)")
    config.addinivalue_line("markers", "slow: Slow tests (skip in quick runs)")


@pytest.fixture
def mock_config():
    """Provide a mock configuration for testing."""
    from unittest.mock import MagicMock
    config = MagicMock()
    config.enable = True
    config.model_id = "test-model"
    config.predict_url = "http://127.0.0.1:9999/predict"
    config.stream_predict_url = "http://127.0.0.1:9999/stream-predict"
    return config
