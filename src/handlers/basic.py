from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
import logging

from src.services.supabase_client import create_user, get_user_admin_teams
from src.keyboards.inline import create_teams_keyboard

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    await create_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name
    )
    
    await message.answer(
        f"👋 Привет, {message.from_user.first_name}!\n\n"
        "🤖 **ChatCopilot** - твой ИИ-ассистент для командной работы!\n\n"
        "🔹 **Создай команду** - `/create_team`\n"
        "🔹 **Присоединись к команде** - `/join_team`\n"
        "🔹 **Мои команды** - `/my_teams`\n"
        "🔹 **Чат с ИИ** - `/chat`\n"
        "🔹 **Помощь** - `/help`\n\n"
        "🚀 Начни с создания команды или присоединения к существующей!",
        parse_mode="Markdown"
    )

@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "🆘 **Помощь по ChatCopilot**\n\n"
        "**Основные команды:**\n"
        "🔹 `/create_team` - создать новую команду\n"
        "🔹 `/join_team` - присоединиться к команде по коду\n"
        "🔹 `/my_teams` - посмотреть свои команды\n"
        "🔹 `/chat` - запустить чат с ИИ\n"
        "🔹 `/cancel` - выйти из текущего режима\n\n"
        "**Управление командами:**\n"
        "🔹 `/link_chat` - привязать групповой чат к команде\n"
        "🔹 `/set_system_message` - настроить системное сообщение\n\n"
        "**Как это работает:**\n"
        "1️⃣ Создайте команду или присоединитесь к существующей\n"
        "2️⃣ Привяжите групповой чат к команде\n"
        "3️⃣ Бот автоматически сохраняет сообщения из чата\n"
        "4️⃣ Используйте `/chat` для вопросов к ИИ по истории\n\n"
        "💡 **Совет**: ИИ анализирует историю сообщений и отвечает на вопросы на основе контекста команды.",
        parse_mode="Markdown"
    )

@router.message(Command("chat"))
async def cmd_chat(message: Message, state: FSMContext):
    """Команда для запуска чата с ИИ"""
    
    # Очищаем состояние
    await state.clear()
    
    try:
        # Получаем команды пользователя где он админ
        admin_teams = await get_user_admin_teams(message.from_user.id)
        
        if not admin_teams:
            await message.answer(
                "❌ **У вас нет команд для чата с ИИ**\n\n"
                "Для использования ИИ-ассистента вам нужно:\n"
                "🔹 Создать команду: `/create_team`\n"
                "🔹 Или присоединиться к команде: `/join_team`\n\n"
                "После создания команды вы сможете общаться с ИИ о её активности.",
                parse_mode="Markdown"
            )
            return
        
        # Создаем клавиатуру с командами
        keyboard = create_teams_keyboard(admin_teams, action_prefix="start_chat")
        
        await message.answer(
            "🤖 **Выберите команду для чата с ИИ**\n\n"
            "Выберите команду, по истории сообщений которой хотите пообщаться с ИИ-ассистентом:\n\n"
            "💬 ИИ проанализирует историю переписки команды и ответит на ваши вопросы",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
        logging.info(f"User {message.from_user.id} requested chat - showing {len(admin_teams)} teams")
        
    except Exception as e:
        logging.error(f"Error in chat command: {e}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при получении списка команд.\n"
            "Попробуйте позже или обратитесь к администратору."
        )

@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    """Универсальная команда для выхода из любого режима"""
    current_state = await state.get_state()
    
    if current_state:
        await state.clear()
        await message.answer(
            "✅ **Режим завершен**\n\n"
            "Вы вышли из текущего режима. Используйте:\n"
            "🔹 `/chat` - для нового чата с ИИ\n"
            "🔹 `/my_teams` - для управления командами\n"
            "🔹 `/help` - для помощи",
            parse_mode="Markdown"
        )
        logging.info(f"User {message.from_user.id} cancelled state: {current_state}")
    else:
        await message.answer(
            "ℹ️ **Нет активного режима**\n\n"
            "Вы не находитесь в специальном режиме.\n"
            "Используйте `/chat` для начала диалога с ИИ.",
            parse_mode="Markdown"
        )
        logging.info(f"User {message.from_user.id} tried to cancel but no active state") 