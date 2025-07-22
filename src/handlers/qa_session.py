from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
import logging

from src.states.team import ChatWithTeam
from src.services.llm import get_answer
from src.services.supabase_client import get_team_by_id, search_messages_by_text

router = Router()

@router.callback_query(F.data.startswith("start_chat:"))
async def start_chat_session(callback: CallbackQuery, state: FSMContext):
    """Handler to start a chat session with AI via callback from the /chat command."""
    team_id = callback.data.split(":")[1]
    
    try:
        team_doc = await get_team_by_id(team_id)
        if not team_doc:
            await callback.message.edit_text("❌ Команда не найдена.")
            return

        team_name = team_doc['name']
        await state.set_state(ChatWithTeam.active)
        await state.update_data(current_team_id=team_id)

        await callback.message.edit_text(
            f"🤖 **Чат с ИИ команды «{team_name}»**\n\n"
            f"✅ **Режим активен!** Теперь все ваши сообщения будут обрабатываться как вопросы к ИИ.\n\n"
            f"💬 **Как это работает:**\n"
            f"🔹 Напишите любой вопрос, и ИИ найдет релевантную информацию в истории переписки команды, чтобы дать ответ.\n"
            f"🔹 Для выхода из режима используйте команду: `/cancel`\n\n"
            f"❓ **Задайте ваш вопрос:**"
        )
        await callback.answer()
        logging.info(f"User {callback.from_user.id} started chat session with team {team_id} ({team_name})")
        
    except Exception as e:
        logging.error(f"Error starting chat session for team {team_id}: {e}", exc_info=True)
        await callback.message.edit_text("❌ **Ошибка при запуске чата.** Попробуйте позже.")

@router.message(ChatWithTeam.active, F.text & ~F.text.startswith("/"))
async def handle_chat_question(message: Message, state: FSMContext, bot: Bot):
    """Handler for questions in AI chat mode."""
    await bot.send_chat_action(message.chat.id, "typing")
    
    data = await state.get_data()
    team_id = data.get("current_team_id")
    question = message.text

    if not team_id:
        await message.answer("❌ **Ошибка сессии.** Пожалуйста, начните чат заново с помощью `/chat`.")
        await state.clear()
        return
    
    logging.info(f"🤖 Processing Q&A question from user {message.from_user.id} for team {team_id}: '{question[:50]}...'")
    
    try:
        team_doc = await get_team_by_id(team_id)
        team_name = team_doc.get('name', 'Unknown')
        custom_system_message = team_doc.get("system_message")

        system_message = custom_system_message or "Ты — ChatCopilot, ИИ-ассистент для командной работы. Твоя задача — помогать пользователям, отвечая на их вопросы на основе предоставленной истории переписки из командных чатов."

        # 1. Search for relevant messages in Supabase
        logging.info(f"🔍 Searching for context for '{question[:30]}...' in team {team_id}")
        relevant_messages = await search_messages_by_text(team_id, question, limit=7)
        
        # 2. Build the context string
        if relevant_messages:
            context = "Найденная история сообщений для ответа на вопрос:\n---\n"
            context += "\n".join([f"{msg['user_name']}: {msg['text']}" for msg in relevant_messages])
            context += "\n---"
            logging.info(f"📚 Found {len(relevant_messages)} relevant messages for context.")
        else:
            context = "В истории команды не найдено релевантной информации по данному вопросу."
            logging.info("📚 No relevant messages found.")

        # 3. Get the answer from vLLM
        full_context = f"System Prompt: {system_message}\n\n{context}"
        logging.info(f"🤖 Requesting answer from vLLM for team {team_id}")
        answer = await get_answer(full_context, question)
        
        # 4. Send the final answer
        footer = f"\n---\n💬 Чат с командой «{team_name}» | `/cancel` для выхода"
        final_answer = answer + footer
        
        await message.answer(final_answer)
        
        logging.info(f"✅ Successfully answered question for user {message.from_user.id} in team {team_id}")

    except Exception as e:
        logging.error(f"❌ Error handling question for team {team_id}: {e}", exc_info=True)
        await message.answer("❌ **Ошибка при обработке вопроса.** Не удалось получить ответ от ИИ. Попробуйте позже.")

@router.message(ChatWithTeam.active, Command("cancel"))
async def cancel_chat_session(message: Message, state: FSMContext):
    """Handler for exiting AI chat mode."""
    data = await state.get_data()
    team_id = data.get("current_team_id")
    team_name = "Unknown"
    if team_id:
        try:
            team_doc = await get_team_by_id(team_id)
            if team_doc:
                team_name = team_doc.get('name', 'Unknown')
        except Exception:
            pass
    
    await state.clear()
    
    await message.answer(
        f"✅ **Чат с ИИ завершен**\n\n"
        f"Вы вышли из режима диалога с командой «{team_name}».\n"
        f"Используйте `/chat` для начала нового диалога."
    )
    logging.info(f"User {message.from_user.id} cancelled chat session with team {team_id} ({team_name})")