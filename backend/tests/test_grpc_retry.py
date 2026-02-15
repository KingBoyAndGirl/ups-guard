"""Tests for gRPC shutdown client retry logic"""
import pytest
import asyncio
import time
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services.lzc_shutdown import LzcGrpcShutdown


@pytest.mark.asyncio
async def test_grpc_shutdown_with_socket_check_failure():
    """Test that shutdown fails gracefully when socket is unreachable"""
    client = LzcGrpcShutdown("/nonexistent/socket.sock", timeout=1.0, max_retries=2)
    
    result = await client.shutdown()
    assert result is False


@pytest.mark.asyncio
async def test_grpc_shutdown_retry_logic():
    """Test that shutdown retries on failure"""
    client = LzcGrpcShutdown("/tmp/test.sock", timeout=1.0, max_retries=3)
    
    # Mock the socket check to always pass
    with patch.object(client, '_check_socket_reachable', new_callable=AsyncMock) as mock_check:
        mock_check.return_value = True
        
        # Mock grpc channel to always fail
        with patch('grpc.aio.insecure_channel') as mock_channel_factory:
            mock_channel = MagicMock()
            mock_stub = AsyncMock()
            
            async def fail_call(*args, **kwargs):
                raise Exception("Connection failed")
            
            mock_stub.side_effect = fail_call
            
            mock_channel.unary_unary.return_value = mock_stub
            mock_channel.close = AsyncMock()
            mock_channel_factory.return_value = mock_channel
            
            result = await client.shutdown()
            
            # Should fail after max retries
            assert result is False
            # Should have called socket check multiple times
            assert mock_check.call_count == 3


@pytest.mark.asyncio
async def test_grpc_shutdown_timeout():
    """Test that shutdown respects timeout"""
    client = LzcGrpcShutdown("/tmp/test.sock", timeout=0.1, max_retries=1)
    
    with patch.object(client, '_check_socket_reachable', new_callable=AsyncMock) as mock_check:
        mock_check.return_value = True
        
        with patch('grpc.aio.insecure_channel') as mock_channel_factory:
            mock_channel = MagicMock()
            mock_stub = AsyncMock()
            
            # Simulate a hanging call
            async def slow_call(*args, **kwargs):
                await asyncio.sleep(10)
            
            mock_stub.side_effect = slow_call
            mock_channel.unary_unary.return_value = mock_stub
            mock_channel.close = AsyncMock()
            mock_channel_factory.return_value = mock_channel
            
            result = await client.shutdown()
            
            # Should timeout and fail
            assert result is False


@pytest.mark.asyncio
async def test_grpc_shutdown_success_on_first_try():
    """Test successful shutdown on first attempt"""
    client = LzcGrpcShutdown("/tmp/test.sock", timeout=1.0, max_retries=3)
    
    with patch.object(client, '_check_socket_reachable', new_callable=AsyncMock) as mock_check:
        mock_check.return_value = True
        
        with patch('grpc.aio.insecure_channel') as mock_channel_factory:
            mock_channel = MagicMock()
            mock_stub = AsyncMock()
            
            # Make the stub callable and return success
            async def mock_call(*args, **kwargs):
                return b""
            
            mock_stub.side_effect = mock_call
            mock_channel.unary_unary.return_value = mock_stub
            mock_channel.close = AsyncMock()
            mock_channel_factory.return_value = mock_channel
            
            result = await client.shutdown()
            
            # Should succeed on first try
            assert result is True
            # Should only check socket once
            assert mock_check.call_count == 1


@pytest.mark.asyncio
async def test_grpc_reboot_retry_logic():
    """Test that reboot also uses retry logic"""
    client = LzcGrpcShutdown("/tmp/test.sock", timeout=1.0, max_retries=2)
    
    with patch.object(client, '_check_socket_reachable', new_callable=AsyncMock) as mock_check:
        mock_check.return_value = False
        
        result = await client.reboot()
        
        # Should fail after retries
        assert result is False
        # Should have attempted socket check max_retries times
        assert mock_check.call_count == 2


@pytest.mark.asyncio
async def test_grpc_exponential_backoff():
    """Test that retries use exponential backoff"""
    client = LzcGrpcShutdown("/tmp/test.sock", timeout=0.1, max_retries=3)
    
    retry_times = []
    
    async def track_time(*args, **kwargs):
        retry_times.append(time.time())
        return False
    
    with patch.object(client, '_check_socket_reachable', new_callable=AsyncMock) as mock_check:
        mock_check.side_effect = track_time
        
        await client.shutdown()
        
        # Should have 3 attempts
        assert len(retry_times) == 3
        
        # Check approximate delays (should be 0, 1, 2 seconds with some tolerance)
        if len(retry_times) >= 2:
            delay1 = retry_times[1] - retry_times[0]
            assert 0.8 < delay1 < 1.5  # ~1 second
        
        if len(retry_times) >= 3:
            delay2 = retry_times[2] - retry_times[1]
            assert 1.5 < delay2 < 3.0  # ~2 seconds
