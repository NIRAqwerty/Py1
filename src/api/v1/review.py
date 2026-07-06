import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.infrastructure.database.session import get_db_session
from src.infrastructure.database.repositories import SqlAlchemyHumanReviewTaskRepository, SqlAlchemyArticleRepository
from src.api.dependencies import get_current_user, RoleChecker
from src.domain.entities import User
from src.infrastructure.queue.arq_config import enqueue_job
from pydantic import BaseModel

router = APIRouter(prefix="/review", tags=["review"])

allow_reviewers = RoleChecker(allowed_roles=["ADMIN", "OPERATOR"])

class ApproveRequest(BaseModel):
    edited_text: Optional[str] = None

@router.get("/tasks")
async def get_tasks(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(allow_reviewers)
) -> list:
    repo = SqlAlchemyHumanReviewTaskRepository(session)
    tasks = await repo.find_pending()
    return tasks

@router.post("/tasks/{task_id}/approve")
async def approve_task(
    task_id: uuid.UUID,
    payload: ApproveRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(allow_reviewers)
) -> dict:
    task_repo = SqlAlchemyHumanReviewTaskRepository(session)
    article_repo = SqlAlchemyArticleRepository(session)
    
    task = await task_repo.find_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Review task not found")
        
    if task.status != "PENDING":
        raise HTTPException(status_code=400, detail="Task already resolved")
        
    article = await article_repo.find_by_id(task.article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Associated article not found")

    task.status = "APPROVED" if not payload.edited_text else "EDITED"
    task.reviewer_id = current_user.id
    task.reviewed_at = datetime.utcnow()
    if payload.edited_text:
        task.edited_text = payload.edited_text
    
    article.status = "READY"
    
    await task_repo.save(task)
    await article_repo.save(article)
    await session.commit()
    
    # Enqueue publication job in background worker queue
    await enqueue_job("publish_post_task", str(article.id))
    
    return {"message": "Task approved and sent to publisher"}

@router.post("/tasks/{task_id}/reject")
async def reject_task(
    task_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(allow_reviewers)
) -> dict:
    task_repo = SqlAlchemyHumanReviewTaskRepository(session)
    article_repo = SqlAlchemyArticleRepository(session)
    
    task = await task_repo.find_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Review task not found")
        
    if task.status != "PENDING":
        raise HTTPException(status_code=400, detail="Task already resolved")
        
    article = await article_repo.find_by_id(task.article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Associated article not found")
        
    task.status = "REJECTED"
    task.reviewer_id = current_user.id
    task.reviewed_at = datetime.utcnow()
    
    article.status = "REJECTED"
    
    await task_repo.save(task)
    await article_repo.save(article)
    await session.commit()
    
    return {"message": "Task rejected"}
