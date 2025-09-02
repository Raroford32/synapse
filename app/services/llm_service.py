"""LLM Service using OpenRouter for model access"""
import json
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    """Service for managing LLM interactions via OpenRouter"""
    
    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
        self.base_url = settings.OPENROUTER_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": settings.OPENROUTER_SITE_URL or "http://localhost:8000",
            "X-Title": settings.OPENROUTER_APP_NAME,
            "Content-Type": "application/json"
        }
        self.client = httpx.AsyncClient(timeout=60.0)
        
        # Model routing configuration
        self.model_map = {
            "synapse": settings.DEFAULT_MODEL,
            "synapse-fast": settings.FAST_MODEL,
            "synapse-smart": settings.SMART_MODEL,
            "synapse-code": settings.CODE_MODEL,
        }
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    def select_model(self, requested_model: str, messages: List[Dict]) -> str:
        """Select appropriate model based on request and strategy"""
        
        # If specific synapse model requested, use mapping
        if requested_model in self.model_map:
            return self.model_map[requested_model]
        
        # If OpenRouter model directly specified, use it
        if "/" in requested_model:
            return requested_model
            
        # Auto-select based on strategy
        if settings.MODEL_SELECTION_STRATEGY == "auto":
            return self._auto_select_model(messages)
        elif settings.MODEL_SELECTION_STRATEGY == "cost-optimized":
            return settings.FAST_MODEL
        elif settings.MODEL_SELECTION_STRATEGY == "performance":
            return settings.SMART_MODEL
        else:
            return settings.DEFAULT_MODEL
    
    def _auto_select_model(self, messages: List[Dict]) -> str:
        """Automatically select model based on message content"""
        
        # Calculate total message length
        total_length = sum(len(msg.get("content", "")) for msg in messages)
        
        # Check for code-related keywords
        code_keywords = ["code", "function", "class", "debug", "error", "implement", "refactor"]
        last_message = messages[-1].get("content", "").lower() if messages else ""
        has_code = any(keyword in last_message for keyword in code_keywords)
        
        # Model selection logic
        if has_code:
            return settings.CODE_MODEL
        elif total_length > 2000 or len(messages) > 10:
            return settings.SMART_MODEL
        else:
            return settings.DEFAULT_MODEL
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "synapse",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate chat completion via OpenRouter"""
        
        selected_model = self.select_model(model, messages)
        
        logger.info(f"Using model: {selected_model} for completion")
        
        payload = {
            "model": selected_model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream,
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
            
        # Add any additional parameters
        payload.update(kwargs)
        
        try:
            if stream:
                return await self._stream_completion(payload)
            else:
                response = await self.client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload
                )
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenRouter API error: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error in chat completion: {str(e)}")
            raise
    
    async def _stream_completion(self, payload: Dict) -> AsyncGenerator:
        """Stream chat completion responses"""
        
        async with self.client.stream(
            "POST",
            f"{self.base_url}/chat/completions",
            headers=self.headers,
            json=payload
        ) as response:
            response.raise_for_status()
            
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        yield chunk
                    except json.JSONDecodeError:
                        continue
    
    async def list_available_models(self) -> List[Dict]:
        """List available models from OpenRouter"""
        
        try:
            response = await self.client.get(
                f"{self.base_url}/models",
                headers=self.headers
            )
            response.raise_for_status()
            data = response.json()
            
            # Add our custom model aliases
            custom_models = [
                {
                    "id": "synapse",
                    "name": "Synapse Auto",
                    "description": "Automatically selects the best model",
                    "actual_model": settings.DEFAULT_MODEL
                },
                {
                    "id": "synapse-fast",
                    "name": "Synapse Fast",
                    "description": "Optimized for speed",
                    "actual_model": settings.FAST_MODEL
                },
                {
                    "id": "synapse-smart",
                    "name": "Synapse Smart",
                    "description": "Optimized for quality",
                    "actual_model": settings.SMART_MODEL
                },
                {
                    "id": "synapse-code",
                    "name": "Synapse Code",
                    "description": "Optimized for coding tasks",
                    "actual_model": settings.CODE_MODEL
                },
            ]
            
            return custom_models + data.get("data", [])
            
        except Exception as e:
            logger.error(f"Error listing models: {str(e)}")
            return []
    
    async def get_usage_stats(self) -> Dict:
        """Get usage statistics from OpenRouter"""
        
        try:
            # OpenRouter doesn't have a direct usage endpoint in their public API
            # This would need to be tracked internally or via their dashboard
            return {
                "status": "available",
                "message": "Usage tracking via OpenRouter dashboard"
            }
        except Exception as e:
            logger.error(f"Error getting usage stats: {str(e)}")
            return {"status": "error", "message": str(e)}