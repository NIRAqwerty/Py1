from abc import ABC, abstractmethod
from typing import NamedTuple, Optional
from src.domain.entities import Article
from src.infrastructure.ai.orchestrator import AIOrchestrator

class CheckResult(NamedTuple):
    passed: bool
    confidence_score: float
    reason: Optional[str] = None

class BaseChecker(ABC):
    def __init__(self, ai_orchestrator: AIOrchestrator) -> None:
        self.ai = ai_orchestrator

    @abstractmethod
    async def check(self, article: Article) -> CheckResult:
        """Perform a quality check on the article."""
        pass
