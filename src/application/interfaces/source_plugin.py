from abc import ABC, abstractmethod
from typing import List
from src.domain.entities import Source, Article

class SourcePlugin(ABC):
    @abstractmethod
    async def fetch_latest(self, source: Source, limit: int = 10) -> List[Article]:
        """Fetch latest posts/articles from the source up to a limit."""
        pass
