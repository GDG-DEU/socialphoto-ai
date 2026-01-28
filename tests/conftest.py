import pytest
import sys
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


def _clear_app_modules():
    """Clear cached app modules to ensure fresh imports."""
    modules_to_clear = [k for k in list(sys.modules.keys()) if k.startswith('app') or k.startswith('src.')]
    for mod in modules_to_clear:
        sys.modules.pop(mod, None)


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    redis_mock = AsyncMock()
    redis_mock.ping = AsyncMock(return_value=True)
    redis_mock.hset = AsyncMock(return_value=True)
    redis_mock.hgetall = AsyncMock(return_value={})
    redis_mock.expire = AsyncMock(return_value=True)
    redis_mock.rpush = AsyncMock(return_value=1)
    redis_mock.close = AsyncMock(return_value=None)
    return redis_mock


@pytest.fixture
def client(mock_redis):
    """Create a test client with mocked dependencies."""
    _clear_app_modules()
    
    with patch("src.services.redis_client.redis_client", mock_redis):
        from app import app
        with TestClient(app) as test_client:
            yield test_client


@pytest.fixture
def client_with_job():
    """Create a test client with a pre-existing job in Redis."""
    _clear_app_modules()
    
    job_data = {
        "job_id": "test-job-123",
        "post_id": "post_456",
        "image_url": "https://example.com/image.jpg",
        "status": "completed",
        "aesthetic_score": "0.85",
        "suggested_tags": '["sunset", "beach", "nature"]'
    }
    
    redis_mock = AsyncMock()
    redis_mock.ping = AsyncMock(return_value=True)
    redis_mock.hgetall = AsyncMock(return_value=job_data)
    redis_mock.hset = AsyncMock(return_value=True)
    redis_mock.expire = AsyncMock(return_value=True)
    redis_mock.rpush = AsyncMock(return_value=1)
    redis_mock.close = AsyncMock(return_value=None)
    
    with patch("src.services.redis_client.redis_client", redis_mock):
        from app import app
        with TestClient(app) as test_client:
            yield test_client
