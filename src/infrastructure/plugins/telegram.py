import os
import uuid
from datetime import datetime
from typing import List
from telethon import TelegramClient
from telethon.sessions import StringSession
from src.application.interfaces.source_plugin import SourcePlugin
from src.domain.entities import Source, Article
from src.config import settings
from src.infrastructure.logging import get_logger

logger = get_logger("POSTS")

class TelegramSourcePlugin(SourcePlugin):
    def __init__(self) -> None:
        self.api_id = settings.telegram_api_id
        self.api_hash = settings.telegram_api_hash
        self.session_str = settings.telegram_session_string

    async def fetch_latest(self, source: Source, limit: int = 10) -> List[Article]:
        if not self.api_id or not self.api_hash or self.api_id == 123456:
            logger.warning(
                "Telegram credentials not configured. Returning mock articles for local testing.",
                source_id=source.id,
            )
            return self._generate_mock_articles(source, limit)

        channel_handle = source.config.get("channel_handle")
        if not channel_handle:
            logger.error("No channel_handle configured for source", source_id=source.id)
            return []

        # Create media directory inside workspace
        download_dir = os.path.abspath(os.path.join("artifacts", "telegram_downloads"))
        os.makedirs(download_dir, exist_ok=True)

        session = StringSession(self.session_str) if self.session_str else "temp_scraping_session"
        client = TelegramClient(session, self.api_id, self.api_hash)
        
        articles = []
        try:
            await client.connect()
            entity = await client.get_entity(channel_handle)
            messages = await client.get_messages(entity, limit=limit)
            
            for msg in messages:
                if not msg.text:
                    continue  # Skip media-only messages without captions

                media_paths = []
                if msg.photo:
                    photo_name = f"{source.id}_{msg.id}.jpg"
                    path = os.path.join(download_dir, photo_name)
                    await client.download_media(msg.photo, file=path)
                    media_paths.append(path)

                article = Article(
                    id=uuid.uuid4(),
                    source_id=source.id,
                    external_id=str(msg.id),
                    raw_text=msg.text,
                    media_urls=media_paths,
                    status="PENDING",
                    fetched_at=datetime.utcnow(),
                    title=f"Telegram Post {msg.id}",
                )
                articles.append(article)
                
        except Exception as e:
            logger.error("Failed to scrape Telegram channel", channel=channel_handle, error=str(e))
        finally:
            await client.disconnect()
            
        return articles

    def _generate_mock_articles(self, source: Source, limit: int) -> List[Article]:
        """Generates realistic mock articles containing clean tech news, spam, and duplicate material."""
        articles = []
        channel_handle = source.config.get("channel_handle", "mock_channel")
        for i in range(1, limit + 1):
            if i == 1:
                # Spam/Ad course sale
                text = (
                    "🔥 SPECIAL OFFER! Learn Python programming with 70% DISCOUNT! "
                    "Master FastAPI, Docker, and AI. Use link: https://fakecourse.com/deal "
                    "Hurry up, only 24 hours left!"
                )
            elif i == 2:
                # Normal tech article
                text = (
                    "Google has introduced Gemini 1.5 Flash, a lighter weight model designed "
                    "for high speed and cost efficiency. It features a native 1-million token "
                    "context window and excels at summarization and multimodal reasoning."
                )
            elif i == 3:
                # Semantic duplicate of i=2
                text = (
                    "Google releases new Gemini 1.5 Flash model! Built for extreme speed, "
                    "efficiency, and low latency, it has a huge 1M token context limit. "
                    "Developers can start using it today for summarization tasks."
                )
            elif i == 4:
                # Toxic/spam post
                text = "We hate these stupid updates. Google is absolute garbage and their new model sucks. Don't buy it."
            else:
                text = (
                    f"This is a standard news summary from {channel_handle} discussing general "
                    f"updates in the tech and startup ecosystems. Post index: {i}."
                )

            articles.append(
                Article(
                    id=uuid.uuid4(),
                    source_id=source.id,
                    external_id=f"mock_{i}",
                    raw_text=text,
                    media_urls=[],
                    status="PENDING",
                    fetched_at=datetime.utcnow(),
                    title=f"Mock Telegram Post {i}",
                )
            )
        return articles
