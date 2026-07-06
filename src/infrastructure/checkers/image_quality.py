import os
import json
from src.domain.entities import Article
from src.infrastructure.checkers.base import BaseChecker, CheckResult
from src.infrastructure.logging import get_logger

logger = get_logger("AI")

class ImageQualityChecker(BaseChecker):
    async def check(self, article: Article) -> CheckResult:
        if not article.media_urls:
            return CheckResult(passed=True, confidence_score=1.0)
            
        for path in article.media_urls:
            if not os.path.exists(path):
                continue
            
            try:
                with open(path, "rb") as f:
                    image_bytes = f.read()

                mime_type = "image/jpeg"
                if path.endswith(".png"):
                    mime_type = "image/png"
                elif path.endswith(".webp"):
                    mime_type = "image/webp"

                prompt = (
                    "Look at this image. Analyze it for any text overlays, watermarks, corporate logos, "
                    "or issues with resolution/quality. Output ONLY a JSON object with this schema:\n"
                    "{\n"
                    "  \"has_watermark_or_logo\": boolean,\n"
                    "  \"is_low_quality\": boolean,\n"
                    "  \"confidence_score\": float (0.0 to 1.0 representing certainty),\n"
                    "  \"reason\": \"description of findings\"\n"
                    "}"
                )

                resp = await self.ai.analyze_image(
                    image_bytes=image_bytes,
                    mime_type=mime_type,
                    prompt=prompt
                )
                
                clean_resp = resp.strip().removeprefix("```json").removesuffix("```").strip()
                data = json.loads(clean_resp)
                
                has_watermark = data.get("has_watermark_or_logo", False)
                low_quality = data.get("is_low_quality", False)
                score = float(data.get("confidence_score", 0.0))
                reason = data.get("reason", "")

                if has_watermark or low_quality:
                    logger.info("Image check failed", path=path, reason=reason)
                    return CheckResult(
                        passed=False,
                        confidence_score=score,
                        reason=f"Image quality issue: {reason}"
                    )
            except Exception as e:
                logger.error("ImageQualityChecker failed", error=str(e), path=path)
                return CheckResult(passed=True, confidence_score=0.0, reason=f"Checker error: {str(e)}")

        return CheckResult(passed=True, confidence_score=1.0)
