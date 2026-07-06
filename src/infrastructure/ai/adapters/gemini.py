import base64
import httpx
from typing import List, Optional
from src.infrastructure.ai.adapters.base import BaseLLMAdapter
from src.infrastructure.logging import get_logger

logger = get_logger("AI")

class GeminiAdapter(BaseLLMAdapter):
    def __init__(self, api_key: str, model_name: str = "gemini-1.5-pro", temperature: float = 0.2):
        self.api_key = api_key
        self.model_name = model_name
        self.temperature = temperature
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"

    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> str:
        temp = temperature if temperature is not None else self.temperature
        url = f"{self.base_url}/{self.model_name}:generateContent?key={self.api_key}"
        
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temp}
        }
        
        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }
            
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return text.strip()
            except Exception as e:
                logger.error("Gemini text generation failed", error=str(e))
                raise

    async def get_embeddings(self, text: str) -> List[float]:
        url = f"{self.base_url}/text-embedding-004:embedContent?key={self.api_key}"
        payload = {
            "model": "models/text-embedding-004",
            "content": {"parts": [{"text": text}]}
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data["embedding"]["values"]
            except Exception as e:
                logger.error("Gemini embedding generation failed", error=str(e))
                raise

    async def analyze_image(self, image_bytes: bytes, mime_type: str, prompt: str) -> str:
        url = f"{self.base_url}/{self.model_name}:generateContent?key={self.api_key}"
        b64_data = self._to_base64(image_bytes)
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inlineData": {
                                "mimeType": mime_type,
                                "data": b64_data
                            }
                        }
                    ]
                }
            ],
            "generationConfig": {"temperature": 0.2}
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return text.strip()
            except Exception as e:
                logger.error("Gemini image analysis failed", error=str(e))
                raise

    async def generate_image(self, prompt: str) -> bytes:
        # Attempt to use Google AI Studio Imagen 3 endpoint
        url = f"{self.base_url}/imagen-3.0-generate-002:generateImages?key={self.api_key}"
        payload = {
            "prompt": prompt,
            "numberOfImages": 1,
            "aspectRatio": "1:1",
            "outputMimeType": "image/jpeg"
        }
        async with httpx.AsyncClient(timeout=90.0) as client:
            try:
                resp = await client.post(url, json=payload)
                if resp.status_code in [403, 404]:
                    raise NotImplementedError("Imagen 3 is not enabled/available on this Gemini key.")
                resp.raise_for_status()
                data = resp.json()
                img_b64 = data["generatedImages"][0]["image"]["imageBytes"]
                return base64.b64decode(img_b64)
            except Exception as e:
                logger.error("Gemini image generation failed", error=str(e))
                raise
