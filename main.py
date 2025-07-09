import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand, BotCommandScopeDefault
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.bot import DefaultBotProperties

from src.services.supabase_client import init_supabase
from src.handlers import basic, team_management, message_ingestion, qa_session
from src.settings import settings

async def main():
    # Bot and Dispatcher setup
    logging.basicConfig(level=logging.INFO)
    bot = Bot(
        token=settings.bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode="HTML")
    )
    dp = Dispatcher()

    # Include routers
    dp.include_router(basic.router)
    dp.include_router(team_management.router)
    dp.include_router(message_ingestion.router)
    dp.include_router(qa_session.router)

    # --- Bot commands ---
    commands = [
        BotCommand(command="start", description="🚀 Перезапустить бота"),
        BotCommand(command="help", description="ℹ️ Справка по командам"),
        BotCommand(command="create_team", description="🌟 Создать новую команду"),
        BotCommand(command="join_team", description="🤝 Присоединиться к команде"),
        BotCommand(command="my_teams", description="👥 Мои команды"),
        BotCommand(command="link_chat", description="🔗 Привязать чат к команде"),
        BotCommand(command="set_system_message", description="✍️ Задать системное сообщение"),
        BotCommand(command="test_pinecone", description="🧪 Тестировать Pinecone (админы)"),
    ]
    await bot.set_my_commands(commands, BotCommandScopeDefault())

    # Initialize external services
    init_supabase()

    # Start polling
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped!")
