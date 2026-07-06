import base64
import httpx
from typing import List, Optional
from src.infrastructure.ai.adapters.base import BaseLLMAdapter
from src.infrastructure.logging import get_logger

logger = get_logger("AI")

class ClaudeAdapter(BaseLLMAdapter):
    def __init__(self, api_key: str, model_name: str = "claude-3-5-sonnet-20240620", temperature: float = 0.2):
        self.api_key = api_key
        self.model_name = model_name
        self.temperature = temperature
        self.base_url = "https://api.anthropic.com/v1"

    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> str:
        temp = temperature if temperature is not None else self.temperature
        url = f"{self.base_url}/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        payload = {
            "model": self.model_name,
            "max_tokens": 1500,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temp
        }
        
        if system_instruction:
            payload["system"] = system_instruction

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                resp = await client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data["content"][0]["text"].strip()
            except Exception as e:
                logger.error("Claude text generation failed", error=str(e))
                raise

    async def get_embeddings(self, text: str) -> List[float]:
        logger.warning("Claude does not support embeddings. Raising NotImplementedError for fallback.")
        raise NotImplementedError("Claude does not natively support embeddings.")

    async def analyze_image(self, image_bytes: bytes, mime_type: str, prompt: str) -> str:
        url = f"{self.base_url}/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        b64_data = self._to_base64(image_bytes)
        
        payload = {
            "model": self.model_name,
            "max_tokens": 1500,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": mime_type,
                                "data": b64_data
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ],
            "temperature": 0.2
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                resp = await client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data["content"][0]["text"].strip()
            except Exception as e:
                logger.error("Claude image analysis failed", error=str(e))
                raise

    async def generate_image(self, prompt: str) -> bytes:
        logger.warning("Claude does not support image generation. Raising NotImplementedError for fallback.")
        raise NotImplementedError("Claude does not natively support image generation.")
