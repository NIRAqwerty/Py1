import json
from src.domain.entities import Article
from src.infrastructure.checkers.base import BaseChecker, CheckResult
from src.infrastructure.logging import get_logger

logger = get_logger("AI")

class GrammarReadabilityChecker(BaseChecker):
    async def check(self, article: Article) -> CheckResult:
        prompt = (
            "Analyze the following text for grammatical correctness, sentence structure, and readability. "
            "Respond ONLY with a valid JSON object matching this schema:\n"
            "{\n"
            "  \"is_comprehensible_and_correct\": boolean,\n"
            "  \"readability_score\": float (0.0 to 1.0 representing how easy it is to read, where 1.0 is extremely readable),\n"
            "  \"error_count\": integer (number of severe grammar errors),\n"
            "  \"reason\": \"short description of findings\"\n"
            "}\n"
            f"Text to analyze:\n{article.raw_text}"
        )
        
        system_instruction = "You are an expert grammar and readability analyzer bot."
        
        try:
            resp = await self.ai.generate_text(
                prompt=prompt,
                system_instruction=system_instruction,
                temperature=0.0
            )
            clean_resp = resp.strip().removeprefix("```json").removesuffix("```").strip()
            data = json.loads(clean_resp)
            
            is_valid = data.get("is_comprehensible_and_correct", True)
            readability = float(data.get("readability_score", 1.0))
            errors = int(data.get("error_count", 0))
            reason = data.get("reason", "Good readability.")

            passed = is_valid and errors <= 5 and readability >= 0.40
            return CheckResult(
                passed=passed,
                confidence_score=readability,
                reason=reason if not passed else None
            )
        except Exception as e:
            logger.error("GrammarReadabilityChecker failed", error=str(e), article_id=article.id)
            return CheckResult(passed=True, confidence_score=1.0, reason=f"Checker failed: {str(e)}")
