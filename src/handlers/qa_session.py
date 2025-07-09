from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
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
    
    team_doc = await get_team_by_id(team_id)
    team_name = team_doc['name']

    await state.set_state(ChatWithTeam.active)
    await state.update_data(current_team_id=team_id)

    await callback.message.edit_text(
        f"Вы начали диалог с ассистентом команды «{team_name}». "
        "Задайте ваш вопрос. Для выхода из режима диалога отправьте /cancel."
    )
    await callback.answer()

@router.message(ChatWithTeam.active, F.text)
async def handle_question(message: Message, state: FSMContext, bot: Bot):
    # --- UX: Show "thinking" animation ---
    await bot.send_chat_action(message.chat.id, "typing")

    data = await state.get_data()
    team_id = data.get("current_team_id")
    question = message.text

    if not team_id:
        await message.answer("Произошла ошибка. Пожалуйста, выберите команду заново через /my_teams.")
        return
    
    # --- RAG Pipeline ---
    try:
        # 0. Get system message
        team_doc = await get_team_by_id(team_id)
        custom_system_message = team_doc.get("system_message")

        # Use custom message or a default one
        system_message = custom_system_message or "Ты — ChatCopilot, ИИ-ассистент для командной работы. Твоя задача — помогать пользователям, отвечая на их вопросы на основе предоставленной истории переписки из командных чатов."

        # 1. Get embedding for the question
        question_vector = await get_embedding(question)

        # 2. Query Pinecone
        query_result = pinecone_index.query(
            namespace=f"team-{team_id}",
            vector=question_vector,
            top_k=3, # Get top 3 most relevant chunks
            include_metadata=True
        )
        
        # 3. Build context
        context = ""
        for match in query_result['matches']:
            context += match['metadata']['text'] + "\n---\n"
        
        # 4. Add recent messages from buffer
        if team_id in message_buffer and message_buffer[team_id]:
            context += "Recent conversation snippets (not yet in knowledge base):\n"
            context += "\n".join(message_buffer[team_id])

        # 5. Add system message to the context for the LLM
        full_context = f"System Prompt: {system_message}\n\nChat History Context:\n{context}"

        # 6. Get answer from LLM
        answer = await get_answer(full_context, question)

        await message.answer(answer)

    except Exception as e:
        logging.error(f"Error handling question for team {team_id}: {e}", exc_info=True)
        await message.answer("Произошла непредвиденная ошибка при обработке вашего запроса. Попробуйте еще раз позже.")
        
@router.message(ChatWithTeam.active, F.text == "/cancel")
async def cancel_chat_session(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Вы вышли из режима диалога. Чтобы снова задать вопрос, используйте /my_teams.") 