import os
import uuid
from typing import List
from src.domain.entities import Article
from src.infrastructure.ai.orchestrator import AIOrchestrator
from src.infrastructure.logging import get_logger

logger = get_logger("IMAGES")

class ImagePipeline:
    def __init__(self, ai_orchestrator: AIOrchestrator) -> None:
        self.ai = ai_orchestrator

    async def process(self, article: Article, rewritten_text: str) -> List[str]:
        """
        Perform processing on images.
        - If article has no images, formulate a prompt based on the content and generate one.
        - If article has images, analyze layout/objects, then generate a fresh unique watermark-free version.
        """
        output_dir = os.path.abspath(os.path.join("artifacts", "generated_images"))
        os.makedirs(output_dir, exist_ok=True)
        
        output_paths = []

        if not article.media_urls:
            logger.info("No source image. Formulating prompt to generate a new illustration.", article_id=article.id)
            try:
                prompt_generator_system = (
                    "You are an art director. Create a detailed, professional image generation prompt "
                    "for DALL-E 3 based on the provided news article content. "
                    "The prompt must describe a clean, modern digital art illustration, vector style, "
                    "no text, no letters, no watermarks, with a harmonious color palette. "
                    "Respond ONLY with the prompt text."
                )
                image_prompt = await self.ai.generate_text(
                    prompt=rewritten_text,
                    system_instruction=prompt_generator_system
                )
                logger.debug("Generated image prompt", prompt=image_prompt)

                image_bytes = await self.ai.generate_image(image_prompt)
                
                file_name = f"{article.id}_generated.jpg"
                save_path = os.path.join(output_dir, file_name)
                with open(save_path, "wb") as f:
                    f.write(image_bytes)
                
                output_paths.append(save_path)
                logger.info("Successfully generated new image", path=save_path)
            except Exception as e:
                logger.error("Failed to generate image from content, falling back to text-only", error=str(e), article_id=article.id)
                
        else:
            logger.info("Source image exists. Recreating to ensure watermark-free uniqueness.", article_id=article.id)
            for path in article.media_urls:
                if not os.path.exists(path):
                    continue
                try:
                    with open(path, "rb") as f:
                        img_bytes = f.read()

                    mime_type = "image/jpeg"
                    if path.endswith(".png"):
                        mime_type = "image/png"
                    elif path.endswith(".webp"):
                        mime_type = "image/webp"

                    analysis_prompt = (
                        "Describe the key objects, layout, theme, and color scheme of this image in detail. "
                        "We will use this description to generate a completely new, unique version. "
                        "Focus on composition and artistic style."
                    )
                    description = await self.ai.analyze_image(img_bytes, mime_type, analysis_prompt)
                    logger.debug("Source image analysis", description=description)

                    prompt_generator_system = (
                        "You are an art director. Create a detailed image generation prompt for a new, "
                        "unique illustration based on the description of a source image. The style should be "
                        "a modern, clean digital illustration, vector style, vibrant colors, absolutely no text, "
                        "no watermarks. Respond ONLY with the prompt."
                    )
                    new_image_prompt = await self.ai.generate_text(
                        prompt=description,
                        system_instruction=prompt_generator_system
                    )
                    logger.debug("Derived new image prompt", prompt=new_image_prompt)

                    new_img_bytes = await self.ai.generate_image(new_image_prompt)

                    file_name = f"{article.id}_recreated_{uuid.uuid4().hex[:8]}.jpg"
                    save_path = os.path.join(output_dir, file_name)
                    with open(save_path, "wb") as f:
                        f.write(new_img_bytes)

                    output_paths.append(save_path)
                    logger.info("Successfully recreated unique image", path=save_path)
                except Exception as e:
                    logger.error("Failed to recreate image, skipping image asset", error=str(e), path=path)
                    
        return output_paths
