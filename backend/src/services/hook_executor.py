"""Hook 执行器服务"""
import asyncio
import logging
import time
from typing import List, Dict, Any, Optional, Callable
from collections import defaultdict
from hooks.registry import get_registry

logger = logging.getLogger(__name__)


class HookExecutor:
    """Hook 执行器，负责按优先级编排执行所有 hook"""
    
    def __init__(
        self, 
        hooks_config: Optional[List[dict]] = None,
        default_timeout: int = 120,
        test_mode: str = "production",
        progress_callback: Optional[Callable] = None,
        cancellation_callback: Optional[Callable[[], bool]] = None
    ):
        """
        初始化 Hook 执行器
        
        Args:
            hooks_config: Hook 配置列表（可选，也可以在 execute_all 时传入）
            default_timeout: 默认超时时间（秒）
            test_mode: 测试模式 - production（生产）/ dry_run（演练）/ mock（模拟）
            progress_callback: WebSocket 进度广播回调函数。
                              应接受一个字典参数，包含 'type' 和 'data' 键。
                              示例: {"type": "hook_progress", "data": {...}}
            cancellation_callback: 取消检查回调函数。返回 True 表示需要取消执行。
        """
        self.registry = get_registry()
        self.hooks_config = hooks_config
        self.default_timeout = default_timeout
        self.test_mode = test_mode
        self.progress_callback = progress_callback
        self.cancellation_callback = cancellation_callback
    
    async def execute_all(self, hooks_config: Optional[List[dict]] = None) -> dict:
        """
        按优先级编排执行所有 hook：
        1. 按 priority 分组（数字小的先执行）
        2. 同优先级的 hook 并行执行（asyncio.gather）
        3. 不同优先级串行执行
        4. 每个 hook 有独立超时（配置项 timeout，默认120秒）
        5. 支持 on_failure 策略：continue（失败继续）/ abort（失败终止）
        
        Args:
            hooks_config: Hook 配置列表（可选，使用初始化时的配置）
        
        Returns:
            执行结果字典：{
                total: 总数,
                success: 成功数,
                failed: 失败数,
                skipped: 跳过数,
                details: [{hook_name, success, error, duration}]
            }
        """
        # 使用传入的配置或初始化时的配置
        if hooks_config is None:
            hooks_config = self.hooks_config
        
        if not hooks_config:
            return {
                "total": 0,
                "success": 0,
                "failed": 0,
                "skipped": 0,
                "details": []
            }
        
        # 过滤出启用的 hook
        enabled_hooks = [h for h in hooks_config if h.get("enabled", True)]
        
        if not enabled_hooks:
            return {
                "total": len(hooks_config),
                "success": 0,
                "failed": 0,
                "skipped": len(hooks_config),
                "details": []
            }
        

        # 按优先级分组
        priority_groups = defaultdict(list)
        for hook_config in enabled_hooks:
            priority = hook_config.get("priority", 99)
            priority_groups[priority].append(hook_config)
        
        # 按优先级排序
        sorted_priorities = sorted(priority_groups.keys())
        
        # 执行结果
        total_count = len(enabled_hooks)
        success_count = 0
        failed_count = 0
        skipped_count = 0
        details = []
        aborted = False
        
        # 按优先级串行执行
        for priority_index, priority in enumerate(sorted_priorities):
            # 检查是否需要取消
            if self.cancellation_callback and self.cancellation_callback():
                aborted = True
            
            if aborted:
                # 如果已经中止，跳过后续所有 hook
                remaining = priority_groups[priority]
                for hook_config in remaining:
                    hook_name = hook_config.get("name", "Unknown")
                    hook_id = hook_config.get("hook_id", "unknown")
                    
                    # 广播跳过状态
                    await self._broadcast_progress(
                        hook_name=hook_name,
                        hook_id=hook_id,
                        status="skipped",
                        priority=priority,
                        duration=0,
                        error="Skipped due to previous failure with abort policy",
                        progress={
                            "total": total_count,
                            "completed": success_count + failed_count + skipped_count,
                            "current_priority": priority
                        }
                    )
                    
                    details.append({
                        "hook_name": hook_name,
                        "success": False,
                        "error": "Skipped due to previous failure with abort policy",
                        "duration": 0
                    })
                    skipped_count += 1
                continue
            

            # 同优先级并行执行
            tasks = []
            hook_configs = priority_groups[priority]
            
            for hook_config in hook_configs:
                # 广播待执行状态
                hook_name = hook_config.get("name", "Unknown")
                hook_id = hook_config.get("hook_id", "unknown")
                
                await self._broadcast_progress(
                    hook_name=hook_name,
                    hook_id=hook_id,
                    status="pending",
                    priority=priority,
                    duration=0,
                    error=None,
                    progress={
                        "total": total_count,
                        "completed": success_count + failed_count + skipped_count,
                        "current_priority": priority
                    }
                )
                
                task = self._execute_single_hook(hook_config)
                tasks.append(task)
            
            # 并行执行同优先级的 hook
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理结果
            for hook_config, result in zip(hook_configs, results):
                hook_name = hook_config.get("name", "Unknown")
                hook_id = hook_config.get("hook_id", "unknown")
                on_failure = hook_config.get("on_failure", "continue")
                
                if isinstance(result, Exception):
                    # 执行过程中发生异常
                    logger.error(f"Hook '{hook_name}' raised exception: {result}")
                    
                    # 广播失败状态
                    await self._broadcast_progress(
                        hook_name=hook_name,
                        hook_id=hook_id,
                        status="failed",
                        priority=priority,
                        duration=0,
                        error=str(result),
                        progress={
                            "total": total_count,
                            "completed": success_count + failed_count + skipped_count + 1,
                            "current_priority": priority
                        }
                    )
                    
                    details.append({
                        "hook_name": hook_name,
                        "success": False,
                        "error": str(result),
                        "duration": 0
                    })
                    failed_count += 1
                    
                    if on_failure == "abort":
                        logger.warning(f"Hook '{hook_name}' failed with abort policy, stopping execution")
                        aborted = True
                else:
                    # 正常执行完成
                    status = "success" if result["success"] else "failed"
                    
                    # 广播执行状态
                    await self._broadcast_progress(
                        hook_name=hook_name,
                        hook_id=hook_id,
                        status=status,
                        priority=priority,
                        duration=result["duration"],
                        error=result.get("error"),
                        progress={
                            "total": total_count,
                            "completed": success_count + failed_count + skipped_count + 1,
                            "current_priority": priority
                        }
                    )
                    
                    details.append(result)
                    
                    if result["success"]:
                        success_count += 1
                    else:
                        failed_count += 1
                        
                        if on_failure == "abort":
                            logger.warning(f"Hook '{hook_name}' failed with abort policy, stopping execution")
                            aborted = True
        

        return {
            "total": total_count,
            "success": success_count,
            "failed": failed_count,
            "skipped": skipped_count,
            "details": details
        }
    
    async def _execute_single_hook(self, hook_config: dict) -> dict:
        """
        执行单个 hook（带重试）
        
        Args:
            hook_config: Hook 配置
        
        Returns:
            执行结果字典：{hook_name, success, error, duration, attempts}
        """
        hook_id = hook_config.get("hook_id")
        hook_name = hook_config.get("name", "Unknown")
        priority = hook_config.get("priority", 99)
        timeout = hook_config.get("timeout", 120)
        config = hook_config.get("config", {})
        
        # 获取重试配置（关机场景使用固定延迟，不使用指数退避）
        max_retries = hook_config.get("max_retries", 2)
        retry_delay = hook_config.get("retry_delay", 5)
        
        start_time = time.time()
        last_error = None
        
        # 重试循环：初始尝试 + max_retries 次重试 = max_retries + 1 次总尝试
        for attempt in range(1, max_retries + 2):
            # 检查是否需要取消
            if self.cancellation_callback and self.cancellation_callback():
                logger.info(f"Hook '{hook_name}' cancelled before attempt {attempt}")
                return {
                    "hook_name": hook_name,
                    "success": False,
                    "error": "Cancelled by user",
                    "duration": time.time() - start_time,
                    "attempts": attempt - 1,
                    "cancelled": True
                }
            
            # 广播执行中状态
            status = "retrying" if attempt > 1 else "executing"
            await self._broadcast_progress(
                hook_name=hook_name,
                hook_id=hook_id,
                status=status,
                priority=priority,
                duration=0,
                error=None,
                progress={
                    "attempt": attempt,
                    "max_attempts": max_retries + 1
                } if attempt > 1 else None
            )
            
            try:
                # 创建 hook 实例
                hook_instance = self.registry.create_instance(hook_id, config)
                
                # 如果是 dry_run 模式，只执行 test_connection 而不是实际执行
                if self.test_mode == "dry_run":
                    success = await asyncio.wait_for(
                        hook_instance.test_connection(),
                        timeout=timeout
                    )
                    duration = time.time() - start_time
                    
                    if success:
                        if attempt > 1:
                            logger.info(f"[DRY-RUN] Hook '{hook_name}' succeeded after {attempt} attempts")
                        return {
                            "hook_name": hook_name,
                            "success": True,
                            "error": None,
                            "duration": duration,
                            "attempts": attempt
                        }
                    else:
                        last_error = "[DRY-RUN] Connection test failed"
                        logger.warning(f"[DRY-RUN] Hook '{hook_name}' failed (attempt {attempt}/{max_retries + 1}): {last_error}")
                else:
                    # 生产模式：实际执行 hook
                    success = await asyncio.wait_for(
                        hook_instance.execute(),
                        timeout=timeout
                    )
                    
                    if success:
                        duration = time.time() - start_time
                        if attempt > 1:
                            logger.info(f"Hook '{hook_name}' succeeded after {attempt} attempts")
                        return {
                            "hook_name": hook_name,
                            "success": True,
                            "error": None,
                            "duration": duration,
                            "attempts": attempt
                        }
                    else:
                        last_error = "Hook execution returned False"
                        logger.warning(f"Hook '{hook_name}' failed (attempt {attempt}/{max_retries + 1}): {last_error}")
            
            except asyncio.TimeoutError:
                last_error = f"Hook execution timed out after {timeout}s"
                logger.warning(f"Hook '{hook_name}' timed out (attempt {attempt}/{max_retries + 1})")
            
            except ValueError as e:
                # 配置验证错误 - 不重试
                duration = time.time() - start_time
                logger.error(f"Hook '{hook_name}' configuration error: {e}")
                return {
                    "hook_name": hook_name,
                    "success": False,
                    "error": f"Configuration error: {str(e)}",
                    "duration": duration,
                    "attempts": attempt
                }
            
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Hook '{hook_name}' raised exception (attempt {attempt}/{max_retries + 1}): {e}")
            
            # 如果还有重试机会，等待后重试
            if attempt <= max_retries:
                # 再次检查是否需要取消
                if self.cancellation_callback and self.cancellation_callback():
                    logger.info(f"Hook '{hook_name}' cancelled during retry wait")
                    return {
                        "hook_name": hook_name,
                        "success": False,
                        "error": "Cancelled by user",
                        "duration": time.time() - start_time,
                        "attempts": attempt,
                        "cancelled": True
                    }
                
                logger.info(f"Retrying hook '{hook_name}' in {retry_delay}s... (attempt {attempt + 1}/{max_retries + 1})")
                
                # 广播重试等待状态
                await self._broadcast_progress(
                    hook_name=hook_name,
                    hook_id=hook_id,
                    status="retry_waiting",
                    priority=priority,
                    duration=0,
                    error=last_error,
                    progress={
                        "attempt": attempt,
                        "max_attempts": max_retries + 1,
                        "retry_delay": retry_delay
                    }
                )
                
                await asyncio.sleep(retry_delay)
        
        # 所有重试都失败
        duration = time.time() - start_time
        logger.error(f"Hook '{hook_name}' failed after {max_retries + 1} attempts: {last_error}")
        return {
            "hook_name": hook_name,
            "success": False,
            "error": last_error or "Unknown error",
            "duration": duration,
            "attempts": max_retries + 1
        }
    
    async def _broadcast_progress(
        self,
        hook_name: str,
        hook_id: str,
        status: str,
        priority: int,
        duration: float,
        error: Optional[str],
        progress: Optional[Dict[str, Any]]
    ):
        """
        广播 hook 执行进度
        
        Args:
            hook_name: Hook 名称
            hook_id: Hook ID
            status: 状态 (pending/executing/success/failed/skipped)
            priority: 优先级
            duration: 执行耗时
            error: 错误信息
            progress: 总体进度信息
        """
        if self.progress_callback:
            try:
                await self.progress_callback({
                    "type": "hook_progress",
                    "data": {
                        "hook_name": hook_name,
                        "hook_id": hook_id,
                        "status": status,
                        "priority": priority,
                        "duration": duration,
                        "error": error,
                        "progress": progress
                    }
                })
            except Exception as e:
                logger.error(f"Failed to broadcast hook progress: {e}")
