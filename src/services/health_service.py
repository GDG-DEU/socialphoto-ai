from typing import Callable, Awaitable, Union
import logging

logger = logging.getLogger(__name__)


class HealthService:
    """Service for managing and checking health of application components."""
    
    def __init__(self):
        self._components: dict[str, Callable[[], Awaitable[bool]]] = {}
    
    def register(self, name: str, check_fn: Callable[[], Awaitable[Union[bool, None]]]) -> None:
        """
        Register a health check function for a component.
        
        Args:
            name: Component name (e.g., "redis", "clip", "pinecone")
            check_fn: Async function that returns True if healthy, raises exception otherwise
        """
        self._components[name] = check_fn
        logger.info(f"Registered health check for: {name}")
    
    def unregister(self, name: str) -> None:
        """Remove a health check."""
        if name in self._components:
            del self._components[name]
            logger.info(f"Unregistered health check for: {name}")
    
    async def check(self, name: str) -> bool:
        """Check health of a specific component."""
        if name not in self._components:
            return False
        try:
            await self._components[name]()
            return True
        except Exception as e:
            logger.warning(f"Health check failed for {name}: {e}")
            return False
    
    async def check_all(self) -> dict[str, bool]:
        """
        Run all registered health checks.
        
        Returns:
            Dict mapping component names to their health status (True/False)
        """
        results = {}
        for name in self._components:
            results[name] = await self.check(name)
        return results
    
    async def get_healthy_components(self) -> list[str]:
        """Return list of component names that are healthy."""
        checks = await self.check_all()
        return [name for name, healthy in checks.items() if healthy]
    
    async def is_healthy(self) -> bool:
        """Return True if all components are healthy."""
        checks = await self.check_all()
        return all(checks.values()) if checks else True
    
    async def get_status(self) -> str:
        """
        Get overall system status.
        
        Returns:
            "online" if all healthy, "degraded" if some unhealthy, "offline" if all unhealthy
        """
        checks = await self.check_all()
        if not checks:
            return "online"
        
        healthy_count = sum(1 for v in checks.values() if v)
        if healthy_count == len(checks):
            return "online"
        elif healthy_count == 0:
            return "offline"
        else:
            return "degraded"


# Singleton instance
health_service = HealthService()
