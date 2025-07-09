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

@router.callback_query(F.data.startswith("chat_with_team:"))
async def start_chat_session(callback: CallbackQuery, state: FSMContext):
    team_id = callback.data.split(":")[1]
    
    try:
        team_doc = await get_team_by_id(team_id)
        team_name = team_doc['name']

        await state.set_state(ChatWithTeam.active)
        await state.update_data(current_team_id=team_id)

        await callback.message.edit_text(
            f"💬 **Диалог с ИИ-ассистентом команды «{team_name}»**\n\n"
            f"Теперь вы можете задавать вопросы по истории сообщений этой команды. "
            f"Я найду релевантную информацию и дам подробный ответ.\n\n"
            f"🔹 Задайте свой вопрос обычным сообщением\n"
            f"🔹 Для выхода из режима диалога отправьте `/cancel`\n\n"
            f"❓ **Чем могу помочь?**",
            parse_mode="Markdown"
        )
        await callback.answer()
        
    except Exception as e:
        logging.error(f"Error starting chat session for team {team_id}: {e}", exc_info=True)
        await callback.message.edit_text("❌ Ошибка при запуске диалога. Попробуйте позже.")

@router.message(ChatWithTeam.active, F.text & ~F.text.startswith("/"))
async def handle_question(message: Message, state: FSMContext, bot: Bot):
    # --- UX: Show "thinking" animation ---
    await bot.send_chat_action(message.chat.id, "typing")

    data = await state.get_data()
    team_id = data.get("current_team_id")
    question = message.text

    if not team_id:
        await message.answer("❌ Произошла ошибка. Пожалуйста, выберите команду заново через /my_teams.")
        await state.clear()
        return
    
    logging.info(f"Processing Q&A question for team {team_id}: {question[:50]}...")
    
    # --- RAG Pipeline ---
    try:
        # 0. Get system message
        team_doc = await get_team_by_id(team_id)
        team_name = team_doc.get('name', 'Unknown')
        custom_system_message = team_doc.get("system_message")

        # Use custom message or a default one
        system_message = custom_system_message or "Ты — ChatCopilot, ИИ-ассистент для командной работы. Твоя задача — помогать пользователям, отвечая на их вопросы на основе предоставленной истории переписки из командных чатов."

        # 1. Get embedding for the question
        question_vector = await get_embedding(question)
        logging.info(f"Created embedding for question in team {team_id}")

        # 2. Query Pinecone
        query_result = pinecone_index.query(
            namespace=f"team-{team_id}",
            vector=question_vector,
            top_k=3, # Get top 3 most relevant chunks
            include_metadata=True
        )
        
        logging.info(f"Pinecone query returned {len(query_result.get('matches', []))} matches for team {team_id}")
        
        # 3. Build context
        context = ""
        for match in query_result['matches']:
            context += match['metadata']['text'] + "\n---\n"
        
        # 4. Add recent messages from buffer
        if team_id in message_buffer and message_buffer[team_id]:
            context += "Recent conversation snippets (not yet in knowledge base):\n"
            context += "\n".join(message_buffer[team_id])
            logging.info(f"Added {len(message_buffer[team_id])} recent messages to context for team {team_id}")

        # 5. Add system message to the context for the LLM
        full_context = f"System Prompt: {system_message}\n\nChat History Context:\n{context}"

        # 6. Get answer from LLM
        answer = await get_answer(full_context, question)
        
        # Add footer with team info
        footer = f"\n\n---\n💬 Диалог с командой «{team_name}» | `/cancel` для выхода"
        
        await message.answer(answer + footer, parse_mode="Markdown")
        logging.info(f"Successfully answered question for team {team_id}")

    except Exception as e:
        logging.error(f"Error handling question for team {team_id}: {e}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при обработке вашего вопроса.\n\n"
            "Возможные причины:\n"
            "• Проблема с подключением к ИИ-сервисам\n"
            "• Временные неполадки векторной базы данных\n"
            "• Недостаточно данных в команде\n\n"
            "Попробуйте:\n"
            "• Переформулировать вопрос\n"
            "• Попробовать позже\n"
            "• Выйти и войти в диалог заново (`/cancel` → `/my_teams`)"
        )

# Global cancel handler (works in any state)
@router.message(Command("cancel"))
async def cancel_any_session(message: Message, state: FSMContext):
    current_state = await state.get_state()
    
    if current_state:
        await state.clear()
        
        if current_state == ChatWithTeam.active.state:
            await message.answer(
                "❌ **Диалог с ИИ-ассистентом завершен**\n\n"
                "Чтобы снова задать вопрос:\n"
                "• Используйте `/my_teams`\n"
                "• Выберите команду\n"
                "• Начните новый диалог",
                parse_mode="Markdown"
            )
        else:
            await message.answer("❌ Текущее действие отменено.")
    else:
        await message.answer("ℹ️ В данный момент нет активных действий для отмены.")

# FSM-specific cancel handler (only in chat state) 
@router.message(ChatWithTeam.active, F.text == "/cancel")
async def cancel_chat_session(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "❌ **Диалог с ИИ-ассистентом завершен**\n\n"
        "Чтобы снова задать вопрос:\n"
        "• Используйте `/my_teams`\n"
        "• Выберите команду\n"
        "• Начните новый диалог",
        parse_mode="Markdown"
    ) 