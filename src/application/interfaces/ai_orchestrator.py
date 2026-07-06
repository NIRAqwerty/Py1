from abc import ABC, abstractmethod
from typing import List, Optional

class LLMAdapter(ABC):
    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """Generate text based on a prompt and system instruction."""
        pass

    @abstractmethod
    async def get_embeddings(self, text: str) -> List[float]:
        """Compute embeddings vector for a given text."""
        pass

    @abstractmethod
    async def analyze_image(self, image_bytes: bytes, mime_type: str, prompt: str) -> str:
        """Analyze an image and extract findings based on a prompt."""
        pass

    @abstractmethod
    async def generate_image(self, prompt: str) -> bytes:
        """Generate a new image based on a prompt, returning raw bytes."""
        pass
