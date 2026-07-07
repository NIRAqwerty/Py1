import os
import httpx
from typing import List, Optional
from src.config import settings
from src.infrastructure.logging import get_logger

logger = get_logger("POSTS")

class TelegramPublisher:
    def __init__(self) -> None:
        self.bot_token = settings.telegram_bot_token
        self.channel_id = settings.publisher.telegram.channel_id
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"

    async def publish(self, text: str, media_paths: List[str]) -> Optional[str]:
        """
        Publishes the rewritten text and media to the configured Telegram channel.
        Returns the published telegram message ID.
        """
        if not self.bot_token or self.bot_token == "your_bot_token_here":
            logger.warning("Telegram Bot Token is not configured. Mocking publication.")
            return "mock_message_id_12345"

        from src.config import Settings
        current_settings = Settings.load()
        channel_id = current_settings.publisher.telegram.channel_id or self.channel_id

        if media_paths and os.path.exists(media_paths[0]):
            # Publish with image
            url = f"{self.base_url}/sendPhoto"
            photo_path = media_paths[0]
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                try:
                    with open(photo_path, "rb") as f:
                        files = {"photo": f}
                        data = {
                            "chat_id": channel_id,
                            "caption": text,
                            "parse_mode": "HTML"
                        }
                        resp = await client.post(url, data=data, files=files)
                        resp.raise_for_status()
                        resp_data = resp.json()
                        msg_id = str(resp_data["result"]["message_id"])
                        logger.info("Published post with photo to Telegram", message_id=msg_id)
                        return msg_id
                except Exception as e:
                    logger.error("Failed to publish photo to Telegram", error=str(e))
                    # Fallback to text-only if photo fails
                    
        # Publish text-only
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": channel_id,
            "text": text,
            "parse_mode": "HTML"
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                resp_data = resp.json()
                msg_id = str(resp_data["result"]["message_id"])
                logger.info("Published text-only post to Telegram", message_id=msg_id)
                return msg_id
            except Exception as e:
                logger.error("Failed to publish text post to Telegram", error=str(e))
                raise
