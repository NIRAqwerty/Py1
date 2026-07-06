import json
from src.domain.entities import Article
from src.infrastructure.checkers.base import BaseChecker, CheckResult
from src.config import settings
from src.infrastructure.logging import get_logger

logger = get_logger("AI")

class ToxicityNsfwChecker(BaseChecker):
    async def check(self, article: Article) -> CheckResult:
        prompt = (
            "Analyze the following text. Determine if it contains any toxic language, hate speech, "
            "insults, threats, violence, NSFW/adult content, or heavy political mudslinging. "
            "Respond ONLY with a valid JSON object matching this schema:\n"
            "{\n"
            "  \"is_toxic_or_nsfw\": boolean,\n"
            "  \"toxicity_score\": float (0.0 to 1.0 representing how severe the toxicity is),\n"
            "  \"reason\": \"short description of findings\"\n"
            "}\n"
            f"Text to analyze:\n{article.raw_text}"
        )
        
        system_instruction = "You are a professional content moderation bot checking for toxicity, adult material, and hate speech."
        
        try:
            resp = await self.ai.generate_text(
                prompt=prompt,
                system_instruction=system_instruction,
                temperature=0.0
            )
            clean_resp = resp.strip().removeprefix("```json").removesuffix("```").strip()
            data = json.loads(clean_resp)
            
            is_toxic = data.get("is_toxic_or_nsfw", False)
            score = float(data.get("toxicity_score", 0.0))
            reason = data.get("reason", "Content is clean.")

            passed = not (is_toxic and score >= settings.thresholds.toxicity_score)
            return CheckResult(
                passed=passed,
                confidence_score=score,
                reason=reason if not passed else None
            )
        except Exception as e:
            logger.error("ToxicityNsfwChecker failed", error=str(e), article_id=article.id)
            return CheckResult(passed=True, confidence_score=0.0, reason=f"Checker failed: {str(e)}")
