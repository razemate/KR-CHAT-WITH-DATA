import time
import asyncio
import logging
from typing import AsyncGenerator, List, Any, Dict, Optional
from vanna.core.llm import LlmService, LlmRequest, LlmResponse, LlmStreamChunk
from vanna.core.tool import ToolSchema
from dataclasses import dataclass
from datetime import datetime, timedelta
import threading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ResilientLlmService")

@dataclass
class ProviderHealth:
    """Tracks health status of an LLM provider"""
    name: str
    is_healthy: bool = True
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    consecutive_failures: int = 0
    circuit_breaker_open: bool = False
    circuit_breaker_open_until: Optional[datetime] = None
    
    def record_success(self):
        self.is_healthy = True
        self.last_success = datetime.now()
        self.consecutive_failures = 0
        self.circuit_breaker_open = False
        self.circuit_breaker_open_until = None
        
    def record_failure(self):
        self.last_failure = datetime.now()
        self.consecutive_failures += 1
        
        # Open circuit breaker after 3 consecutive failures
        if self.consecutive_failures >= 3:
            self.circuit_breaker_open = True
            self.circuit_breaker_open_until = datetime.now() + timedelta(minutes=5)
            self.is_healthy = False
            
    def is_available(self) -> bool:
        """Check if provider is available for requests"""
        if self.circuit_breaker_open:
            if datetime.now() > self.circuit_breaker_open_until:
                # Circuit breaker timeout expired, try again
                self.circuit_breaker_open = False
                self.circuit_breaker_open_until = None
                return True
            return False
        return self.is_healthy

class ResilientLlmService(LlmService):
    """
    Wraps multiple LLM services (primary and a list of fallbacks) with:
    1. RPM Limiting (Sliding Window)
    2. Exponential Backoff (retries on HTTP 429)
    3. Seamless Sequential Fallback (switches to the next provider on failure)
    4. Circuit Breaker Pattern (prevents cascading failures)
    5. Provider Health Monitoring
    6. Comprehensive Logging
    """
    def __init__(self, primary: LlmService, fallbacks: List[LlmService], rpm_limit: int = 1000):
        self.primary = primary
        self.fallbacks = fallbacks
        self.rpm_limit = rpm_limit
        self.requests = []
        self.logger = logger
        
        # Initialize provider health tracking
        self.provider_health: Dict[str, ProviderHealth] = {}
        all_services = [primary] + fallbacks
        for service in all_services:
            name = self._get_provider_name(service)
            self.provider_health[name] = ProviderHealth(name=name)
            
        # Thread lock for health tracking
        self._health_lock = threading.Lock()
        
    def _get_provider_name(self, service: LlmService) -> str:
        """Get a descriptive name for the provider"""
        service_name = service.__class__.__name__
        if "Gemini" in service_name: 
            return "Gemini"
        elif "Cerebras" in service_name: 
            return "Cerebras"
        elif "Ollama" in service_name: 
            return "Ollama Cloud"
        elif hasattr(service, 'base_url'):
            if "groq" in str(service.base_url).lower(): 
                return "Groq"
            elif "openrouter" in str(service.base_url).lower(): 
                return "OpenRouter"
        return service_name

    async def _throttle(self):
        if self.rpm_limit <= 0:
            self.rpm_limit = 1

        now = time.time()
        self.requests = [req_time for req_time in self.requests if now - req_time < 60.0]
        
        if len(self.requests) >= self.rpm_limit:
            sleep_time = 60.0 - (now - self.requests[0])
            if sleep_time > 0:
                self.logger.info(f"[Throttler] Traffic near limit ({len(self.requests)} RPM). Queueing request for {sleep_time:.2f}s...")
                await asyncio.sleep(sleep_time)
            
            now = time.time()
            self.requests = [req_time for req_time in self.requests if now - req_time < 60.0]

        self.requests.append(time.time())

    async def send_request(self, request: LlmRequest) -> LlmResponse:
        await self._throttle()
        
        all_services = [self.primary] + self.fallbacks
        
        for idx, service in enumerate(all_services):
            provider_name = self._get_provider_name(service)
            health = self.provider_health[provider_name]
            
            # Skip if circuit breaker is open
            if not health.is_available():
                self.logger.warning(f"[CircuitBreaker] {provider_name} is circuit-broken, skipping")
                continue
                
            retries = 3 if idx == 0 else 1  # Only retry primary
            base_delay = 2.0
            
            for attempt in range(retries):
                try:
                    response = await service.send_request(request)
                    # Record success
                    with self._health_lock:
                        health.record_success()
                    self.logger.info(f"[Success] {provider_name} responded successfully")
                    return response
                    
                except Exception as e:
                    error_str = str(e).lower()
                    is_rate_limit = any(q in error_str for q in ["429", "quota", "rate limit", "resource exhausted"])
                    
                    # Record failure
                    with self._health_lock:
                        health.record_failure()
                    
                    if is_rate_limit and attempt < retries - 1:
                        delay = base_delay * (2 ** attempt)
                        self.logger.warning(f"[RateLimit] {provider_name} hit limit. Retrying in {delay}s... (Attempt {attempt+1}/{retries})")
                        await asyncio.sleep(delay)
                        continue
                    
                    # If this is the last service or not a rate limit we can retry, move to next fallback
                    self.logger.error(f"[Fallback] {provider_name} failed (Attempt {attempt+1}/{retries}): {e}")
                    break  # Break out of retry loop, move to next service in all_services
        
        # Log final failure with all provider statuses
        provider_status = ", ".join([f"{name}: {'✓' if health.is_available() else '✗'}" for name, health in self.provider_health.items()])
        raise Exception(f"All LLM services failed to respond. Provider status: {provider_status}")

    async def stream_request(self, request: LlmRequest) -> AsyncGenerator[LlmStreamChunk, None]:
        await self._throttle()
        
        all_services = [self.primary] + self.fallbacks
        tried_providers = []
        
        for idx, service in enumerate(all_services):
            provider_name = self._get_provider_name(service)
            health = self.provider_health[provider_name]
            
            # Skip if circuit breaker is open
            if not health.is_available():
                self.logger.warning(f"[CircuitBreaker] {provider_name} is circuit-broken, skipping")
                tried_providers.append(f"{provider_name} (circuit-broken)")
                continue
                
            tried_providers.append(provider_name)
            retries = 2 if idx == 0 else 1  # Reduced retries for faster failover
            base_delay = 2.0
            success = False
            
            self.logger.info(f"[ResilientLlm] Trying {provider_name}")
            
            for attempt in range(retries):
                try:
                    stream_gen = service.stream_request(request)
                    # We need to peek at the first chunk to ensure the service is working
                    first_chunk = await stream_gen.__anext__()
                    yield first_chunk
                    
                    async for chunk in stream_gen:
                        yield chunk
                    
                    # Record success
                    with self._health_lock:
                        health.record_success()
                    self.logger.info(f"[Success] {provider_name} stream completed successfully")
                    success = True
                    break  # Success!
                    
                except StopAsyncIteration:
                    success = True
                    break
                except Exception as e:
                    error_str = str(e).lower()
                    is_rate_limit = any(q in error_str for q in ["429", "quota", "rate limit", "resource exhausted"])
                    
                    # Record failure
                    with self._health_lock:
                        health.record_failure()
                    
                    if is_rate_limit and attempt < retries - 1:
                        delay = base_delay * (2 ** attempt)
                        self.logger.warning(f"[RateLimit] {provider_name} Stream hit limit. Retrying in {delay}s... (Attempt {attempt+1}/{retries})")
                        await asyncio.sleep(delay)
                        continue
                    
                    self.logger.error(f"[Fallback] {provider_name} failed: {e}")
                    break  # Move to next fallback
            
            if success:
                return

        # If we get here, everything failed.
        providers_str = ", ".join(tried_providers)
        provider_status = ", ".join([f"{name}: {'✓' if health.is_available() else '✗'}" for name, health in self.provider_health.items()])
        error_msg = f"⚠️ Systems are currently overloaded or API limits have been reached across all providers ({providers_str}). Provider status: {provider_status}. Please wait a few moments and try again."
        
        self.logger.error(f"[ResilientLlm] All providers failed: {providers_str}")
        yield LlmStreamChunk(content=f"\n\n{error_msg}")

    async def validate_tools(self, tools: List[ToolSchema]) -> List[str]:
        return await self.primary.validate_tools(tools)
        
    def get_provider_health_status(self) -> Dict[str, Dict[str, Any]]:
        """Get current health status of all providers"""
        status = {}
        for name, health in self.provider_health.items():
            status[name] = {
                "is_healthy": health.is_healthy,
                "is_available": health.is_available(),
                "last_success": health.last_success.isoformat() if health.last_success else None,
                "last_failure": health.last_failure.isoformat() if health.last_failure else None,
                "consecutive_failures": health.consecutive_failures,
                "circuit_breaker_open": health.circuit_breaker_open,
                "circuit_breaker_open_until": health.circuit_breaker_open_until.isoformat() if health.circuit_breaker_open_until else None,
            }
        return status
        
    def reset_circuit_breaker(self, provider_name: str) -> bool:
        """Manually reset circuit breaker for a specific provider"""
        if provider_name in self.provider_health:
            with self._health_lock:
                health = self.provider_health[provider_name]
                health.circuit_breaker_open = False
                health.circuit_breaker_open_until = None
                health.is_healthy = True
                health.consecutive_failures = 0
                self.logger.info(f"[CircuitBreaker] Manually reset circuit breaker for {provider_name}")
                return True
        return False
