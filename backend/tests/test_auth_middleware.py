"""Tests for authentication middleware"""
import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from middleware.auth import AuthMiddleware


@pytest.mark.asyncio
async def test_auth_middleware_allows_excluded_paths():
    """Test that excluded paths don't require authentication"""
    app = FastAPI()
    token = "test-token-123"
    middleware = AuthMiddleware(app, token)
    
    # Create mock request for excluded path
    class MockRequest:
        def __init__(self, path):
            self.url = type('URL', (), {'path': path})()
            self.headers = {}
    
    async def mock_next(request):
        return JSONResponse({"status": "ok"})
    
    # Test /health (excluded)
    request = MockRequest("/health")
    response = await middleware(request, mock_next)
    assert response.status_code == 200
    
    # Test / (excluded)
    request = MockRequest("/")
    response = await middleware(request, mock_next)
    assert response.status_code == 200
    
    # Test /ws (excluded prefix)
    request = MockRequest("/ws/connect")
    response = await middleware(request, mock_next)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_auth_middleware_requires_token_for_api():
    """Test that /api/* routes require authentication"""
    app = FastAPI()
    token = "test-token-123"
    middleware = AuthMiddleware(app, token)
    
    class MockRequest:
        def __init__(self, path, headers=None):
            self.url = type('URL', (), {'path': path})()
            self.headers = headers or {}
    
    async def mock_next(request):
        return JSONResponse({"status": "ok"})
    
    # Test /api/status without token
    request = MockRequest("/api/status")
    response = await middleware(request, mock_next)
    assert response.status_code == 401
    
    # Test /api/status with invalid token
    request = MockRequest("/api/status", {"Authorization": "Bearer wrong-token"})
    response = await middleware(request, mock_next)
    assert response.status_code == 401
    
    # Test /api/status with valid token
    request = MockRequest("/api/status", {"Authorization": f"Bearer {token}"})
    response = await middleware(request, mock_next)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_auth_middleware_validates_header_format():
    """Test that authorization header format is validated"""
    app = FastAPI()
    token = "test-token-123"
    middleware = AuthMiddleware(app, token)
    
    class MockRequest:
        def __init__(self, path, headers=None):
            self.url = type('URL', (), {'path': path})()
            self.headers = headers or {}
    
    async def mock_next(request):
        return JSONResponse({"status": "ok"})
    
    # Test with missing Bearer prefix
    request = MockRequest("/api/status", {"Authorization": token})
    response = await middleware(request, mock_next)
    assert response.status_code == 401
    
    # Test with empty Authorization
    request = MockRequest("/api/status", {"Authorization": ""})
    response = await middleware(request, mock_next)
    assert response.status_code == 401
    
    # Test with only "Bearer"
    request = MockRequest("/api/status", {"Authorization": "Bearer"})
    response = await middleware(request, mock_next)
    assert response.status_code == 401
