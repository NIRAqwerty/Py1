from typing import Any
from arq import create_pool
from arq.connections import RedisSettings
from src.config import settings

redis_settings = RedisSettings.from_dsn(settings.redis.url)

async def enqueue_job(job_name: str, *args: Any, **kwargs: Any) -> None:
    pool = await create_pool(redis_settings)
    try:
        await pool.enqueue_job(job_name, *args, **kwargs)
    finally:
        await pool.close()


