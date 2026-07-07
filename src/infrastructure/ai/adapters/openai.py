import base64
import httpx
import asyncio
from typing import List, Optional
from src.infrastructure.ai.adapters.base import BaseLLMAdapter
from src.infrastructure.logging import get_logger

logger = get_logger("AI")

class OpenAIAdapter(BaseLLMAdapter):
    def __init__(self, api_key: str, model_name: str = "gpt-4o", temperature: float = 0.2, base_url: str = "https://api.openai.com/v1"):
        self.api_key = api_key
        self.model_name = model_name
        self.temperature = temperature
        self.base_url = base_url

    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> str:
        temp = temperature if temperature is not None else self.temperature
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        from src.config import settings

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temp,
            "max_tokens": settings.llm.max_tokens
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    resp = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        json=payload,
                    )
                    
                    if resp.status_code == 429:
                        wait_time = (attempt + 1) * 2.0
                        logger.warning(f"Rate limited (429) on OpenRouter. Retrying in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        continue

                    if resp.status_code == 402 and "openrouter.ai" in self.base_url:
                        logger.warning("Credits depleted on OpenRouter. Attempting fallback to 'openrouter/free' model.")
                        payload["model"] = "openrouter/free"
                        resp = await client.post(
                            f"{self.base_url}/chat/completions",
                            headers={"Authorization": f"Bearer {self.api_key}"},
                            json=payload,
                        )
                        if resp.status_code == 429:
                            wait_time = (attempt + 1) * 2.0
                            logger.warning(f"Rate limited (429) on OpenRouter fallback. Retrying in {wait_time}s...")
                            await asyncio.sleep(wait_time)
                            continue

                    resp.raise_for_status()
                    data = resp.json()
                    content = data["choices"][0]["message"].get("content")
                    return content.strip() if content else ""
                except Exception as e:
                    if attempt == max_retries - 1:
                        logger.error("OpenAI text generation failed after retries", error=str(e))
                        raise
            
            raise RuntimeError("OpenAI text generation failed: all attempts were rate limited or failed.")

    async def get_embeddings(self, text: str) -> List[float]:
        url = f"{self.base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "text-embedding-3-small",
            "input": text
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data["data"][0]["embedding"]
            except Exception as e:
                logger.error("OpenAI embedding generation failed", error=str(e))
                raise

    async def analyze_image(self, image_bytes: bytes, mime_type: str, prompt: str) -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        b64_data = self._to_base64(image_bytes)
        
        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{b64_data}"
                            }
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
                content = data["choices"][0]["message"].get("content")
                return content.strip() if content else ""
            except Exception as e:
                logger.error("OpenAI image analysis failed", error=str(e))
                raise

    async def generate_image(self, prompt: str) -> bytes:
        url = f"{self.base_url}/images/generations"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "dall-e-3",
            "prompt": prompt,
            "n": 1,
            "size": "1024x1024",
            "response_format": "b64_json"
        }

        async with httpx.AsyncClient(timeout=90.0) as client:
            try:
                resp = await client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
                img_b64 = data["data"][0]["b64_json"]
                return base64.b64decode(img_b64)
            except Exception as e:
                logger.error("OpenAI image generation failed", error=str(e))
                raise
