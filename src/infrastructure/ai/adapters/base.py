import base64
from typing import List, Optional
from src.application.interfaces.ai_orchestrator import LLMAdapter

class BaseLLMAdapter(LLMAdapter):
    def _to_base64(self, data: bytes) -> str:
        return base64.b64encode(data).decode("utf-8")

    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> str:
        raise NotImplementedError

    async def get_embeddings(self, text: str) -> List[float]:
        raise NotImplementedError

    async def analyze_image(self, image_bytes: bytes, mime_type: str, prompt: str) -> str:
        raise NotImplementedError

    async def generate_image(self, prompt: str) -> bytes:
        raise NotImplementedError
