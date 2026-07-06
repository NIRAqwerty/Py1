import json
from src.domain.entities import Article
from src.infrastructure.checkers.base import BaseChecker, CheckResult
from src.infrastructure.logging import get_logger

logger = get_logger("AI")

class FactChecker(BaseChecker):
    async def check(self, article: Article) -> CheckResult:
        prompt = (
            "You are a professional fact-checker. Analyze the following text for factual contradictions, "
            "extreme unsupported claims, logical fallacies, or clear signs of hallucination/falsification. "
            "Respond ONLY with a valid JSON object matching this schema:\n"
            "{\n"
            "  \"is_verifiable_and_consistent\": boolean,\n"
            "  \"contradiction_score\": float (0.0 to 1.0 representing how severe the contradictions/hallucinations are),\n"
            "  \"reason\": \"short description of findings\"\n"
            "}\n"
            f"Text to analyze:\n{article.raw_text}"
        )
        
        system_instruction = "You are a professional news verification bot."
        
        try:
            resp = await self.ai.generate_text(
                prompt=prompt,
                system_instruction=system_instruction,
                temperature=0.0
            )
            clean_resp = resp.strip().removeprefix("```json").removesuffix("```").strip()
            data = json.loads(clean_resp)
            
            is_valid = data.get("is_verifiable_and_consistent", True)
            score = float(data.get("contradiction_score", 0.0))
            reason = data.get("reason", "No issues found.")

            passed = is_valid and score < 0.70
            return CheckResult(
                passed=passed,
                confidence_score=1.0 - score,
                reason=reason if not passed else None
            )
        except Exception as e:
            logger.error("FactChecker failed", error=str(e), article_id=article.id)
            return CheckResult(passed=True, confidence_score=0.0, reason=f"Checker failed: {str(e)}")
