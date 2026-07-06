import json
from src.domain.entities import Article
from src.infrastructure.checkers.base import BaseChecker, CheckResult
from src.config import settings
from src.infrastructure.logging import get_logger

logger = get_logger("AI")

class AdSpamChecker(BaseChecker):
    async def check(self, article: Article) -> CheckResult:
        prompt = (
            "Analyze the following text. Determine if it contains any advertisements, sponsored content, "
            "promotional deals, referral codes/links, product sales pitch, or casino/betting/crypto spam. "
            "Respond ONLY with a valid JSON object matching this schema:\n"
            "{\n"
            "  \"is_ad_or_spam\": boolean,\n"
            "  \"confidence_score\": float (0.0 to 1.0 representing how confident you are that this is an ad/spam),\n"
            "  \"reason\": \"short description of findings\"\n"
            "}\n"
            f"Text to analyze:\n{article.raw_text}"
        )
        
        system_instruction = "You are a professional content moderation bot that detects advertising, spam, and clickbait."
        
        try:
            resp = await self.ai.generate_text(
                prompt=prompt,
                system_instruction=system_instruction,
                temperature=0.0
            )
            clean_resp = resp.strip().removeprefix("```json").removesuffix("```").strip()
            data = json.loads(clean_resp)
            
            is_ad = data.get("is_ad_or_spam", False)
            score = float(data.get("confidence_score", 0.0))
            reason = data.get("reason", "No reason provided.")

            passed = not (is_ad and score >= settings.thresholds.ad_score)
            return CheckResult(
                passed=passed,
                confidence_score=score,
                reason=reason if not passed else None
            )
        except Exception as e:
            logger.error("AdSpamChecker failed", error=str(e), article_id=article.id)
            return CheckResult(passed=True, confidence_score=0.0, reason=f"Checker failed: {str(e)}")
