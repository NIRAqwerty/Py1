import asyncio
import logging
from datetime import datetime
from typing import Set, Optional
import uuid

from aiogram import Bot, Dispatcher, Router, html
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from sqlalchemy import select

from src.config import settings
from src.infrastructure.database.session import async_session_maker
from src.infrastructure.database.models import UserModel
from src.infrastructure.database.repositories import (
    SqlAlchemyHumanReviewTaskRepository,
    SqlAlchemyArticleRepository,
)
from src.infrastructure.security import verify_password
from src.infrastructure.queue.arq_config import enqueue_job
from src.infrastructure.logging import get_logger

logger = get_logger("BOT")

router = Router()
authorized_users: Set[int] = set()

class EditDraftState(StatesGroup):
    waiting_for_draft_text = State()

def load_allowed_users() -> None:
    """Loads statically allowed Telegram user IDs from configuration."""
    if settings.telegram_allowed_users:
        for item in settings.telegram_allowed_users.split(","):
            item = item.strip()
            if item.isdigit():
                authorized_users.add(int(item))
                logger.info("Added statically allowed Telegram user ID", user_id=item)

load_allowed_users()

def is_authorized(user_id: int) -> bool:
    return user_id in authorized_users

async def check_auth(message: Message) -> bool:
    if not is_authorized(message.from_user.id):
        await message.answer(
            "🔒 <b>Доступ ограничен.</b> Вы должны авторизоваться в системе с помощью команды:\n"
            "<code>/login &lt;username&gt; &lt;password&gt;</code>\n"
            "Или ваш Telegram ID должен быть добавлен в список <code>TELEGRAM_ALLOWED_USERS</code>.",
            parse_mode="HTML"
        )
        return False
    return True

async def check_auth_callback(callback: CallbackQuery) -> bool:
    if not is_authorized(callback.from_user.id):
        await callback.answer("🔒 Доступ ограничен. Пожалуйста, выполните команду /login.", show_alert=True)
        return False
    return True

@router.message(Command("start", "help"))
async def cmd_start(message: Message) -> None:
    welcome_text = (
        "🤖 <b>Telegram AI Publisher Management Bot</b>\n\n"
        "Этот бот позволяет управлять публикацией и модерировать статьи, находящиеся на проверке.\n\n"
        "<b>Команды:</b>\n"
        "📝 /tasks — Показать список ожидающих задач\n"
        "🔑 <code>/login &lt;username&gt; &lt;password&gt;</code> — Авторизоваться в системе\n"
        "❓ /help — Справка"
    )
    await message.answer(welcome_text, parse_mode="HTML")

@router.message(Command("login"))
async def cmd_login(message: Message) -> None:
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer(
            "⚠️ Использование: <code>/login &lt;username&gt; &lt;password&gt;</code>\n"
            "Пример: <code>/login operator operator123</code>",
            parse_mode="HTML"
        )
        return
    
    username = args[1]
    password = args[2]
    
    async with async_session_maker() as session:
        stmt = select(UserModel).filter(UserModel.username == username)
        res = await session.execute(stmt)
        user = res.scalar_one_or_none()
        
        if user and verify_password(password, user.hashed_password):
            authorized_users.add(message.from_user.id)
            await message.answer(
                f"✅ Успешный вход! Вы вошли как <b>{html.bold(user.username)}</b> ({user.role}).\n"
                "Теперь вы можете использовать команду /tasks для просмотра задач.",
                parse_mode="HTML"
            )
            logger.info("Telegram user logged in successfully", telegram_user_id=message.from_user.id, db_username=username)
        else:
            await message.answer("❌ Неверное имя пользователя или пароль.")

@router.message(Command("tasks"))
async def cmd_tasks(message: Message) -> None:
    if not await check_auth(message):
        return
    
    async with async_session_maker() as session:
        task_repo = SqlAlchemyHumanReviewTaskRepository(session)
        tasks = await task_repo.find_pending()
        
        if not tasks:
            await message.answer("✅ Нет ожидающих задач для проверки.")
            return
        
        await message.answer(f"📋 Найдено задач на проверку: {len(tasks)}")
        for t in tasks:
            reasons_str = ", ".join(t.reasons)
            text = (
                f"📝 <b>Задача:</b> <code>{t.id}</code>\n"
                f"<b>AI Confidence Score:</b> <code>{t.confidence_score:.2f}</code>\n"
                f"<b>Причины проверки:</b> {html.quote(reasons_str)}\n"
                f"<b>Дата создания:</b> {t.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="👁️ Показать текст", callback_data=f"task_view:{t.id}"),
                    InlineKeyboardButton(text="✅ Одобрить", callback_data=f"task_approve:{t.id}"),
                ],
                [
                    InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"task_edit:{t.id}"),
                    InlineKeyboardButton(text="❌ Отклонить", callback_data=f"task_reject:{t.id}"),
                ]
            ])
            await message.answer(text, reply_markup=keyboard, parse_mode="HTML")

@router.callback_query(lambda c: c.data and c.data.startswith("task_view:"))
async def process_task_view(callback: CallbackQuery) -> None:
    if not await check_auth_callback(callback):
        return
    
    task_id_str = callback.data.split(":")[1]
    task_id = uuid.UUID(task_id_str)
    
    async with async_session_maker() as session:
        task_repo = SqlAlchemyHumanReviewTaskRepository(session)
        article_repo = SqlAlchemyArticleRepository(session)
        
        task = await task_repo.find_by_id(task_id)
        if not task:
            await callback.answer("Ошибка: Задача не найдена", show_alert=True)
            return
            
        article = await article_repo.find_by_id(task.article_id)
        raw_text = article.raw_text if article else "Текст не найден"
        
        response_text = (
            f"ℹ️ <b>Детали задачи:</b> <code>{task_id}</code>\n\n"
            f"📌 <b>Исходный текст:</b>\n{html.quote(raw_text[:600])}{'...' if len(raw_text) > 600 else ''}\n\n"
            f"✍️ <b>Черновик:</b>\n{html.quote(task.edited_text or '')}"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Одобрить черновик", callback_data=f"task_approve:{task_id}"),
                InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"task_edit:{task_id}"),
            ],
            [
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"task_reject:{task_id}")
            ]
        ])
        
        await callback.message.answer(response_text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()

@router.callback_query(lambda c: c.data and c.data.startswith("task_approve:"))
async def process_task_approve(callback: CallbackQuery) -> None:
    if not await check_auth_callback(callback):
        return
    
    task_id_str = callback.data.split(":")[1]
    task_id = uuid.UUID(task_id_str)
    
    async with async_session_maker() as session:
        task_repo = SqlAlchemyHumanReviewTaskRepository(session)
        article_repo = SqlAlchemyArticleRepository(session)
        
        task = await task_repo.find_by_id(task_id)
        if not task or task.status != "PENDING":
            await callback.answer("Задача уже решена или не найдена", show_alert=True)
            return
            
        article = await article_repo.find_by_id(task.article_id)
        if not article:
            await callback.answer("Связанная статья не найдена", show_alert=True)
            return
            
        task.status = "APPROVED" if not task.edited_text else "EDITED"
        task.reviewed_at = datetime.utcnow()
        
        article.status = "READY"
        
        await task_repo.save(task)
        await article_repo.save(article)
        await session.commit()
        
        await enqueue_job("publish_post_task", str(article.id))
        
        await callback.message.edit_text(
            f"✅ <b>Задача {task_id} одобрена и отправлена на публикацию!</b>",
            parse_mode="HTML"
        )
        await callback.answer("Одобрено!")

@router.callback_query(lambda c: c.data and c.data.startswith("task_reject:"))
async def process_task_reject(callback: CallbackQuery) -> None:
    if not await check_auth_callback(callback):
        return
    
    task_id_str = callback.data.split(":")[1]
    task_id = uuid.UUID(task_id_str)
    
    async with async_session_maker() as session:
        task_repo = SqlAlchemyHumanReviewTaskRepository(session)
        article_repo = SqlAlchemyArticleRepository(session)
        
        task = await task_repo.find_by_id(task_id)
        if not task or task.status != "PENDING":
            await callback.answer("Задача уже решена или не найдена", show_alert=True)
            return
            
        article = await article_repo.find_by_id(task.article_id)
        if not article:
            await callback.answer("Связанная статья не найдена", show_alert=True)
            return
            
        task.status = "REJECTED"
        task.reviewed_at = datetime.utcnow()
        
        article.status = "REJECTED"
        
        await task_repo.save(task)
        await article_repo.save(article)
        await session.commit()
        
        await callback.message.edit_text(
            f"❌ <b>Задача {task_id} отклонена.</b>",
            parse_mode="HTML"
        )
        await callback.answer("Отклонено")

@router.callback_query(lambda c: c.data and c.data.startswith("task_edit:"))
async def process_task_edit(callback: CallbackQuery, state: FSMContext) -> None:
    if not await check_auth_callback(callback):
        return
        
    task_id_str = callback.data.split(":")[1]
    
    await state.set_state(EditDraftState.waiting_for_draft_text)
    await state.update_data(task_id=task_id_str)
    
    await callback.message.answer(
        "✏️ Отправьте новый текст для этого черновика в следующем сообщении. "
        "Для отмены отправьте /cancel."
    )
    await callback.answer()

@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is None:
        return
        
    await state.clear()
    await message.answer("Отменено.")

@router.message(EditDraftState.waiting_for_draft_text)
async def process_new_draft_text(message: Message, state: FSMContext) -> None:
    if not await check_auth(message):
        await state.clear()
        return
        
    state_data = await state.get_data()
    task_id_str = state_data.get("task_id")
    if not task_id_str:
        await message.answer("Произошла ошибка (ID задачи не найден). Попробуйте заново.")
        await state.clear()
        return
        
    task_id = uuid.UUID(task_id_str)
    new_text = message.text
    
    async with async_session_maker() as session:
        task_repo = SqlAlchemyHumanReviewTaskRepository(session)
        article_repo = SqlAlchemyArticleRepository(session)
        
        task = await task_repo.find_by_id(task_id)
        if not task or task.status != "PENDING":
            await message.answer("Задача уже решена или не найдена.")
            await state.clear()
            return
            
        article = await article_repo.find_by_id(task.article_id)
        if not article:
            await message.answer("Связанная статья не найдена.")
            await state.clear()
            return
            
        task.status = "EDITED"
        task.edited_text = new_text
        task.reviewed_at = datetime.utcnow()
        
        article.status = "READY"
        
        await task_repo.save(task)
        await article_repo.save(article)
        await session.commit()
        
        await enqueue_job("publish_post_task", str(article.id))
        
        await message.answer("✅ Черновик отредактирован и отправлен на публикацию!")
        await state.clear()

bot_task: Optional[asyncio.Task] = None
bot_instance: Optional[Bot] = None
dp_instance: Optional[Dispatcher] = None

async def run_bot() -> None:
    global bot_instance, dp_instance
    token = settings.telegram_bot_token
    if not token or token == "your_bot_token_here":
        logger.warning("Telegram Bot Token is not configured. Telegram management bot will not start.")
        return
        
    logger.info("Initializing Telegram management bot")
    bot_instance = Bot(token=token)
    dp_instance = Dispatcher(storage=MemoryStorage())
    dp_instance.include_router(router)
    
    try:
        await dp_instance.start_polling(bot_instance)
    except asyncio.CancelledError:
        logger.info("Telegram management bot polling task cancelled")
    except Exception as e:
        logger.error("Error in Telegram management bot polling", error=str(e))
    finally:
        await bot_instance.session.close()

def start_bot() -> None:
    global bot_task
    bot_task = asyncio.create_task(run_bot())
    logger.info("Telegram management bot task started in background")

async def stop_bot() -> None:
    global bot_task, dp_instance, bot_instance
    logger.info("Stopping Telegram management bot")
    if dp_instance:
        await dp_instance.stop_polling()
    if bot_task:
        bot_task.cancel()
        try:
            await bot_task
        except asyncio.CancelledError:
            pass
        bot_task = None
