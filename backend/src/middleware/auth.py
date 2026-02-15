"""API Token Authentication Middleware"""
import logging
import os
from typing import Callable
from fastapi import Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AuthMiddleware:
    """Bearer Token Authentication Middleware"""
    
    def __init__(self, app, api_token: str):
        self.app = app
        self.api_token = api_token
        # 开发模式下跳过认证
        self.skip_auth = os.environ.get("MOCK_MODE", "").lower() in ("true", "1", "yes")
        if self.skip_auth:
            logger.warning("MOCK_MODE enabled: API authentication is disabled")
        # Paths that don't require authentication
        self.exclude_paths = {"/health", "/", "/docs", "/openapi.json", "/redoc"}
        self.exclude_prefixes = ["/ws"]
    
    async def __call__(self, request: Request, call_next: Callable):
        """Process request with authentication check"""
        path = request.url.path
        
        # 开发模式跳过所有认证
        if self.skip_auth:
            return await call_next(request)

        # Check if path is excluded from authentication
        if path in self.exclude_paths:
            return await call_next(request)
        
        # Check if path starts with excluded prefix
        for prefix in self.exclude_prefixes:
            if path.startswith(prefix):
                return await call_next(request)
        
        # All /api/ routes require authentication
        if path.startswith("/api/"):
            # Get Authorization header
            auth_header = request.headers.get("Authorization")
            
            if not auth_header:
                logger.warning(f"Unauthorized access attempt to {path}: No Authorization header")
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Missing Authorization header"},
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Validate Bearer token
            parts = auth_header.split()
            if len(parts) != 2 or parts[0].lower() != "bearer":
                logger.warning(f"Unauthorized access attempt to {path}: Invalid Authorization format")
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Invalid Authorization header format. Expected: Bearer <token>"},
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            token = parts[1]
            if token != self.api_token:
                logger.warning(f"Unauthorized access attempt to {path}: Invalid token")
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Invalid API token"},
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            logger.debug(f"Authenticated access to {path}")
        
        return await call_next(request)
