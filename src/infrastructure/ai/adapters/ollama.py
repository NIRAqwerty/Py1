import base64
import httpx
from typing import List, Optional
from src.infrastructure.ai.adapters.base import BaseLLMAdapter
from src.infrastructure.logging import get_logger

logger = get_logger("AI")

class OllamaAdapter(BaseLLMAdapter):
    def __init__(self, base_url: str = "http://localhost:11434", model_name: str = "llama3"):
        self.base_url = base_url
        self.model_name = model_name

    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> str:
        url = f"{self.base_url}/api/chat"
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
        }
        if temperature is not None:
            payload["options"] = {"temperature": temperature}

        async with httpx.AsyncClient(timeout=90.0) as client:
            try:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data["message"]["content"].strip()
            except Exception as e:
                logger.error("Ollama text generation failed", error=str(e))
                raise

    async def get_embeddings(self, text: str) -> List[float]:
        url = f"{self.base_url}/api/embeddings"
        payload = {
            "model": self.model_name,
            "prompt": text
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data["embedding"]
            except Exception as e:
                logger.error("Ollama embedding generation failed", error=str(e))
                raise

    async def analyze_image(self, image_bytes: bytes, mime_type: str, prompt: str) -> str:
        url = f"{self.base_url}/api/chat"
        b64_data = self._to_base64(image_bytes)
        
        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "images": [b64_data]
                }
            ],
            "stream": False
        }
        async with httpx.AsyncClient(timeout=90.0) as client:
            try:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data["message"]["content"].strip()
            except Exception as e:
                logger.error("Ollama image analysis failed", error=str(e))
                raise

    async def generate_image(self, prompt: str) -> bytes:
        logger.warning("Ollama does not support image generation. Raising NotImplementedError.")
        raise NotImplementedError("Ollama does not support image generation.")
