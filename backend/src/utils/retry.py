"""通用重试工具"""
import asyncio
import logging
import functools
from typing import Optional, Tuple, Type

logger = logging.getLogger(__name__)


async def async_retry(
    coro_func,
    *args,
    max_retries: int = 3,
    base_delay: float = 1.0,
    exponential_backoff: bool = False,
    max_delay: float = 30.0,
    retry_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    operation_name: str = "operation",
    **kwargs
):
    """通用异步重试函数
    
    Args:
        coro_func: 要重试的异步函数
        max_retries: 最大重试次数
        base_delay: 基础延迟（秒）
        exponential_backoff: 是否使用指数退避
        max_delay: 最大延迟（秒）
        retry_exceptions: 触发重试的异常类型
        operation_name: 操作名称（用于日志）
    
    Returns:
        函数返回值
        
    Note:
        max_retries 指的是失败后的重试次数，不包括初始尝试。
        例如 max_retries=2 表示：1次初始尝试 + 最多2次重试 = 最多3次尝试
    """
    last_exception = None
    
    # 初始尝试 + max_retries 次重试 = max_retries + 1 次总尝试
    for attempt in range(1, max_retries + 2):
        try:
            return await coro_func(*args, **kwargs)
        except retry_exceptions as e:
            last_exception = e
            if attempt <= max_retries:
                if exponential_backoff:
                    delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                else:
                    delay = base_delay
                logger.warning(
                    f"{operation_name} failed (attempt {attempt}/{max_retries + 1}), "
                    f"retrying in {delay:.1f}s: {e}"
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    f"{operation_name} failed after {max_retries + 1} attempts: {e}"
                )
    
    raise last_exception


def with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    exponential_backoff: bool = False,
    max_delay: float = 30.0,
    retry_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    operation_name: Optional[str] = None
):
    """重试装饰器
    
    用法：
        @with_retry(max_retries=3, base_delay=1.0)
        async def my_function():
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            name = operation_name or func.__qualname__
            return await async_retry(
                func, *args,
                max_retries=max_retries,
                base_delay=base_delay,
                exponential_backoff=exponential_backoff,
                max_delay=max_delay,
                retry_exceptions=retry_exceptions,
                operation_name=name,
                **kwargs
            )
        return wrapper
    return decorator
