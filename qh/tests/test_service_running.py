"""Tests for the service_running context manager."""

import pytest
import requests
from qh import mk_app, service_running, ServiceInfo


def add(x: int, y: int) -> int:
    """Add two numbers."""
    return x + y


def test_service_running_with_app():
    """Test service_running with a FastAPI app."""
    app = mk_app([add])

    with service_running(app=app, port=8101) as info:
        assert isinstance(info, ServiceInfo)
        assert info.url == 'http://127.0.0.1:8101'
        assert not info.was_already_running
        assert info.thread is not None
        assert info.app is app

        # Test the service works
        response = requests.post(f'{info.url}/add', json={'x': 10, 'y': 20})
        assert response.status_code == 200
        assert response.json() == 30


def test_service_running_already_running():
    """Test service_running with an already-running external service."""
    # Using GitHub API as a reliably running external service
    with service_running(url='https://api.github.com') as info:
        assert info.url == 'https://api.github.com'
        assert info.was_already_running
        assert info.thread is None
        assert info.app is None

        # Verify service is accessible
        response = requests.get(f'{info.url}/users/octocat')
        assert response.status_code == 200


def test_service_running_validation():
    """Test that service_running validates arguments correctly."""
    # No arguments provided
    with pytest.raises(ValueError, match="Must provide one of"):
        with service_running():
            pass

    # Multiple arguments provided
    app = mk_app([add])
    with pytest.raises(ValueError, match="Cannot provide multiple"):
        with service_running(app=app, url='http://localhost:8000'):
            pass


def test_service_running_url_not_running():
    """Test that service_running fails when URL is not running and no launcher."""
    with pytest.raises(RuntimeError, match="Service not running"):
        with service_running(url='http://localhost:9999'):
            pass


def test_service_info_return_value():
    """Test that service_running returns ServiceInfo with correct attributes."""
    app = mk_app([add])

    with service_running(app=app, port=8102) as info:
        # Check all attributes exist and have correct types
        assert hasattr(info, 'url')
        assert hasattr(info, 'was_already_running')
        assert hasattr(info, 'thread')
        assert hasattr(info, 'app')

        assert isinstance(info.url, str)
        assert isinstance(info.was_already_running, bool)
        assert info.thread is not None
        assert info.app is app
