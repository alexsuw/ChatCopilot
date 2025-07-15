from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
import logging

from src.states.team import ChatWithTeam
from src.services.vector_db import get_embedding, pinecone_index
from src.services.llm import get_answer
from src.handlers.message_ingestion import message_buffer
from src.services.supabase_client import get_team_by_id

router = Router()

@router.callback_query(F.data.startswith("start_chat:"))
async def start_chat_session(callback: CallbackQuery, state: FSMContext):
    """Обработчик для начала чата с ИИ через callback от команды /chat"""
    team_id = callback.data.split(":")[1]
    
    try:
        team_doc = await get_team_by_id(team_id)
        team_name = team_doc['name']

        # Устанавливаем состояние чата
        await state.set_state(ChatWithTeam.active)
        await state.update_data(current_team_id=team_id)

        await callback.message.edit_text(
            f"🤖 **Чат с ИИ команды «{team_name}»**\n\n"
            f"✅ **Режим активен!** Теперь все ваши сообщения будут обрабатываться как вопросы к ИИ.\n\n"
            f"💬 **Как это работает:**\n"
            f"🔹 Напишите любой вопрос обычным сообщением\n"
            f"🔹 ИИ найдет релевантную информацию в истории команды\n"
            f"🔹 Вы получите подробный ответ на основе переписки\n\n"
            f"🔹 **Для выхода из режима:** `/cancel`\n\n"
            f"❓ **Задайте ваш первый вопрос:**",
            parse_mode="Markdown"
        )
        await callback.answer()
        
        logging.info(f"User {callback.from_user.id} started chat session with team {team_id} ({team_name})")
        
    except Exception as e:
        logging.error(f"Error starting chat session for team {team_id}: {e}", exc_info=True)
        await callback.message.edit_text(
            "❌ **Ошибка при запуске чата**\n\n"
            "Не удалось начать диалог с ИИ. Попробуйте:\n"
            "🔹 Попробовать позже\n"
            "🔹 Использовать `/chat` еще раз\n"
            "🔹 Обратиться к администратору",
            parse_mode="Markdown"
        )

@router.message(ChatWithTeam.active, F.text & ~F.text.startswith("/"))
async def handle_chat_question(message: Message, state: FSMContext, bot: Bot):
    """Обработчик вопросов в режиме чата с ИИ"""
    
    # Показываем анимацию набора
    await bot.send_chat_action(message.chat.id, "typing")
    
    data = await state.get_data()
    team_id = data.get("current_team_id")
    question = message.text

    if not team_id:
        await message.answer(
            "❌ **Ошибка сессии**\n\n"
            "Не удалось определить команду. Попробуйте:\n"
            "🔹 Выйти из режима: `/cancel`\n"
            "🔹 Запустить чат заново: `/chat`",
            parse_mode="Markdown"
        )
        await state.clear()
        return
    
    logging.info(f"🤖 Processing Q&A question from user {message.from_user.id} for team {team_id}: '{question[:50]}...'")
    
    # RAG Pipeline
    try:
        # 1. Получаем информацию о команде
        team_doc = await get_team_by_id(team_id)
        team_name = team_doc.get('name', 'Unknown')
        custom_system_message = team_doc.get("system_message")

        # Используем кастомное сообщение или дефолтное
        system_message = custom_system_message or "Ты — ChatCopilot, ИИ-ассистент для командной работы. Твоя задача — помогать пользователям, отвечая на их вопросы на основе предоставленной истории переписки из командных чатов."

        logging.info(f"📋 Using system message for team {team_id}: {system_message[:100]}...")

        # 2. Создаем эмбеддинг для вопроса
        question_vector = await get_embedding(question)
        logging.info(f"🧠 Created embedding for question in team {team_id}")

        # 3. Ищем в Pinecone
        query_result = pinecone_index.query(
            namespace=f"team-{team_id}",
            vector=question_vector,
            top_k=3,  # Топ-3 релевантных чанка
            include_metadata=True
        )
        
        logging.info(f"📊 Pinecone query returned {len(query_result.get('matches', []))} matches for team {team_id}")
        
        # 4. Формируем контекст
        context = ""
        for match in query_result['matches']:
            context += match['metadata']['text'] + "\n---\n"
        
        # 5. Добавляем недавние сообщения из буфера
        if team_id in message_buffer and message_buffer[team_id]:
            context += "Recent conversation snippets (not yet in knowledge base):\n"
            context += "\n".join(message_buffer[team_id])
            logging.info(f"📝 Added {len(message_buffer[team_id])} recent messages to context for team {team_id}")

        # 6. Формируем полный контекст для LLM
        full_context = f"System Prompt: {system_message}\n\nChat History Context:\n{context}"

        # 7. Получаем ответ от Gemini
        logging.info(f"🤖 Requesting answer from Gemini for team {team_id}")
        answer = await get_answer(full_context, question)
        
        # 8. Формируем итоговый ответ
        footer = f"\n---\n💬 Чат с командой «{team_name}» | `/cancel` для выхода"
        final_answer = answer + footer
        
        await message.answer(final_answer, parse_mode="Markdown")
        
        logging.info(f"✅ Successfully answered question for user {message.from_user.id} in team {team_id}")
        logging.info(f"📏 Answer length: {len(answer)} chars")

    except Exception as e:
        logging.error(f"❌ Error handling question for team {team_id}: {e}", exc_info=True)
        await message.answer(
            f"❌ **Ошибка при обработке вопроса**\n\n"
            f"Не удалось получить ответ от ИИ. Возможные причины:\n"
            f"🔹 Проблема с подключением к ИИ-сервисам\n"
            f"🔹 Временные неполадки векторной базы данных\n"
            f"🔹 Недостаточно данных в команде\n\n"
            f"**Попробуйте:**\n"
            f"🔹 Переформулировать вопрос\n"
            f"🔹 Попробовать позже\n"
            f"🔹 Выйти и войти в чат заново: `/cancel` → `/chat`\n\n"
            f"---\n💬 Чат с командой «{team_name}» | `/cancel` для выхода",
            parse_mode="Markdown"
        )

@router.message(ChatWithTeam.active, Command("cancel"))
async def cancel_chat_session(message: Message, state: FSMContext):
    """Обработчик выхода из чата с ИИ"""
    
    data = await state.get_data()
    team_id = data.get("current_team_id")
    
    try:
        if team_id:
            team_doc = await get_team_by_id(team_id)
            team_name = team_doc.get('name', 'Unknown')
        else:
            team_name = "Unknown"
    except:
        team_name = "Unknown"
    
    await state.clear()
    
    await message.answer(
        f"✅ **Чат с ИИ завершен**\n\n"
        f"Вы вышли из режима диалога с командой «{team_name}».\n\n"
        f"**Доступные команды:**\n"
        f"🔹 `/chat` - новый чат с ИИ\n"
        f"🔹 `/my_teams` - управление командами\n"
        f"🔹 `/help` - помощь\n\n"
        f"🤖 Спасибо за использование ChatCopilot!",
        parse_mode="Markdown"
    )
    
    logging.info(f"User {message.from_user.id} cancelled chat session with team {team_id} ({team_name})")

# Обработчик для старых callback (для обратной совместимости)
@router.callback_query(F.data.startswith("chat_with_team:"))
async def legacy_chat_handler(callback: CallbackQuery, state: FSMContext):
    """Обработчик для старых callback кнопок - перенаправляет на новую логику"""
    
    await callback.message.edit_text(
        "🔄 **Обновленная логика чата**\n\n"
        "Теперь для чата с ИИ используйте команду `/chat`.\n\n"
        "🤖 Это более надежный способ общения с ИИ-ассистентом!",
        parse_mode="Markdown"
    )
    await callback.answer("Используйте команду /chat для чата с ИИ")
    
    logging.info(f"User {callback.from_user.id} used legacy chat handler - redirected to /chat command") 