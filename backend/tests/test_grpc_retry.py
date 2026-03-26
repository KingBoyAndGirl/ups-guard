"""Tests for gRPC shutdown client retry logic"""
import pytest
import asyncio
import time
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services.lzc_shutdown import LzcApiGatewayShutdown


@pytest.mark.asyncio
async def test_grpc_shutdown_retry_logic():
    """Test that shutdown retries on failure"""
    client = LzcApiGatewayShutdown(
        gateway_address="test.gateway:81",
        timeout=1.0,
        max_retries=3
    )

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
        # Should have tried max_retries times
        assert mock_channel_factory.call_count == 3


@pytest.mark.asyncio
async def test_grpc_shutdown_timeout():
    """Test that shutdown respects timeout"""
    client = LzcApiGatewayShutdown(
        gateway_address="test.gateway:81",
        timeout=0.1,
        max_retries=1
    )

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
    client = LzcApiGatewayShutdown(
        gateway_address="test.gateway:81",
        timeout=1.0,
        max_retries=3
    )

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
        # Should only connect once
        assert mock_channel_factory.call_count == 1


@pytest.mark.asyncio
async def test_grpc_reboot_retry_logic():
    """Test that reboot also uses retry logic"""
    client = LzcApiGatewayShutdown(
        gateway_address="test.gateway:81",
        timeout=1.0,
        max_retries=2
    )

    with patch('grpc.aio.insecure_channel') as mock_channel_factory:
        mock_channel = MagicMock()
        mock_stub = AsyncMock()

        async def fail_call(*args, **kwargs):
            raise Exception("Connection failed")

        mock_stub.side_effect = fail_call
        mock_channel.unary_unary.return_value = mock_stub
        mock_channel.close = AsyncMock()
        mock_channel_factory.return_value = mock_channel

        result = await client.reboot()
        
        # Should fail after retries
        assert result is False
        # Should have attempted max_retries times
        assert mock_channel_factory.call_count == 2


@pytest.mark.asyncio
async def test_grpc_exponential_backoff():
    """Test that retries use exponential backoff"""
    client = LzcApiGatewayShutdown(
        gateway_address="test.gateway:81",
        timeout=0.1,
        max_retries=3
    )

    retry_times = []
    
    with patch('grpc.aio.insecure_channel') as mock_channel_factory:
        mock_channel = MagicMock()
        mock_stub = AsyncMock()

        async def fail_and_track(*args, **kwargs):
            retry_times.append(time.time())
            raise Exception("Connection failed")

        mock_stub.side_effect = fail_and_track
        mock_channel.unary_unary.return_value = mock_stub
        mock_channel.close = AsyncMock()
        mock_channel_factory.return_value = mock_channel

        await client.shutdown()
        
        # Should have 3 attempts
        assert len(retry_times) == 3
        
        # Check approximate delays (should be 0, 1, 2 seconds with some tolerance)
        if len(retry_times) >= 2:
            delay1 = retry_times[1] - retry_times[0]
            assert 0.8 < delay1 < 1.5  # ~1 second
        
        if len(retry_times) >= 3:
            delay2 = retry_times[2] - retry_times[1]
            assert 1.8 < delay2 < 2.5  # ~2 seconds


@pytest.mark.asyncio
async def test_gateway_address_auto_detection():
    """Test automatic gateway address detection"""
    import os

    # Test with LZCAPP_API_GATEWAY_ADDRESS
    with patch.dict(os.environ, {"LZCAPP_API_GATEWAY_ADDRESS": "custom.gateway:81"}):
        client = LzcApiGatewayShutdown()
        assert client.gateway_address == "custom.gateway:81"

    # Test with LAZYCAT_APP_ID
    with patch.dict(os.environ, {"LAZYCAT_APP_ID": "my.app"}, clear=True):
        # Clear the gateway address env var
        os.environ.pop("LZCAPP_API_GATEWAY_ADDRESS", None)
        client = LzcApiGatewayShutdown()
        assert client.gateway_address == "app.my.app.lzcapp:81"


@pytest.mark.asyncio
async def test_gateway_address_explicit():
    """Test explicit gateway address"""
    client = LzcApiGatewayShutdown(gateway_address="explicit.gateway:81")
    assert client.gateway_address == "explicit.gateway:81"
