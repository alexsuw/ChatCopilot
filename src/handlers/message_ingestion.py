import asyncio
import logging
import uuid
from collections import defaultdict
from aiogram import Router, F
from aiogram.types import Message

from src.services.supabase_client import get_linked_chat
from src.services.vector_db import get_embedding, upsert_vector

router = Router()
# УБИРАЕМ фильтр роутера - будем проверять в самом обработчике
# router.message.filter(F.chat.type.in_({"group", "supergroup"}))

# In-memory buffer for messages
# {team_id: [message_text_1, message_text_2, ...]}
message_buffer = defaultdict(list)
# To avoid processing the same chunk multiple times
processing_locks = defaultdict(asyncio.Lock)

CHUNK_SIZE = 5  # Number of messages to batch together

# Мониторинг сообщений для диагностики
monitoring_enabled = False
monitoring_chat_id = None

@router.message(F.text & F.text.startswith("/monitor_messages"))
async def monitor_messages_command(message: Message):
    global monitoring_enabled, monitoring_chat_id
    
    if message.chat.type != "private":
        await message.answer("❌ Эта команда работает только в приватном чате с ботом.")
        return
    
    monitoring_enabled = not monitoring_enabled
    monitoring_chat_id = message.chat.id if monitoring_enabled else None
    
    if monitoring_enabled:
        await message.answer(
            "🔍 **Мониторинг сообщений ВКЛЮЧЕН**\n\n"
            "Теперь я буду показывать все получаемые сообщения из групповых чатов.\n"
            "Отправьте `/monitor_messages` еще раз для отключения."
        )
    else:
        await message.answer("⏹️ Мониторинг сообщений ОТКЛЮЧЕН")

@router.message(F.text)
async def message_handler(message: Message):
    global monitoring_enabled, monitoring_chat_id
    
    chat_id = message.chat.id
    chat_title = message.chat.title or "Unknown Chat"
    chat_type = message.chat.type
    user_name = message.from_user.first_name or "Unknown User"
    
    # Enhanced logging with chat type
    logging.info(f"📝 New message from {user_name} in chat {chat_id} ({chat_title}) [type: {chat_type}]")
    
    # Мониторинг для диагностики
    if monitoring_enabled and monitoring_chat_id:
        monitor_text = (
            f"📨 **Получено сообщение:**\n"
            f"• От: {user_name}\n"
            f"• Чат: {chat_title} (ID: {chat_id})\n"
            f"• Тип: {chat_type}\n"
            f"• Текст: {message.text[:50]}{'...' if len(message.text) > 50 else ''}\n"
        )
        
        # Отправляем уведомление в чат мониторинга
        try:
            from aiogram import Bot
            bot = Bot.get_current()
            await bot.send_message(monitoring_chat_id, monitor_text, parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Ошибка отправки уведомления мониторинга: {e}")
    
    # Check if it's a group/supergroup chat
    if chat_type not in ["group", "supergroup"]:
        logging.debug(f"🚫 Ignoring message from {chat_type} chat {chat_id}")
        
        # Уведомление мониторинга
        if monitoring_enabled and monitoring_chat_id:
            try:
                from aiogram import Bot
                bot = Bot.get_current()
                await bot.send_message(monitoring_chat_id, f"❌ Игнорируется - тип чата: {chat_type}", parse_mode="Markdown")
            except Exception as e:
                logging.error(f"Ошибка отправки уведомления мониторинга: {e}")
        return
    
    try:
        # Get linked chat document
        chat_doc = await get_linked_chat(chat_id)
        if not chat_doc:
            # Chat not linked to any team, ignore.
            logging.debug(f"🔗 Chat {chat_id} ({chat_title}) not linked to any team, ignoring message")
            
            # Уведомление мониторинга
            if monitoring_enabled and monitoring_chat_id:
                try:
                    from aiogram import Bot
                    bot = Bot.get_current()
                    await bot.send_message(monitoring_chat_id, f"🔗 Чат не привязан к команде", parse_mode="Markdown")
                except Exception as e:
                    logging.error(f"Ошибка отправки уведомления мониторинга: {e}")
            return
        
        team_id = chat_doc['team_id']
        logging.info(f"✅ Chat {chat_id} ({chat_title}) is linked to team {team_id}")
        
    except Exception as e:
        # Chat not linked to any team, ignore.
        logging.warning(f"❌ Error getting linked chat for {chat_id} ({chat_title}): {e}")
        
        # Уведомление мониторинга
        if monitoring_enabled and monitoring_chat_id:
            try:
                from aiogram import Bot
                bot = Bot.get_current()
                await bot.send_message(monitoring_chat_id, f"❌ Ошибка привязки: {e}", parse_mode="Markdown")
            except Exception as e:
                logging.error(f"Ошибка отправки уведомления мониторинга: {e}")
        return

    if not team_id:
        logging.warning(f"⚠️ Chat {chat_id} ({chat_title}) has empty team_id, ignoring")
        return # Ignore messages from chats not linked to any team

    # Add message to buffer
    full_message = f"{user_name}: {message.text}"
    message_buffer[team_id].append(full_message)
    
    current_buffer_size = len(message_buffer[team_id])
    logging.info(f"📊 Added message to team {team_id} buffer. Current size: {current_buffer_size}/{CHUNK_SIZE}")

    # Уведомление мониторинга
    if monitoring_enabled and monitoring_chat_id:
        try:
            from aiogram import Bot
            bot = Bot.get_current()
            await bot.send_message(
                monitoring_chat_id, 
                f"✅ Добавлено в буфер команды {team_id}\n"
                f"📊 Размер буфера: {current_buffer_size}/{CHUNK_SIZE}", 
                parse_mode="Markdown"
            )
        except Exception as e:
            logging.error(f"Ошибка отправки уведомления мониторинга: {e}")

    # If buffer is full, process the chunk
    if current_buffer_size >= CHUNK_SIZE:
        logging.info(f"🚀 Buffer full for team {team_id}, processing chunk")
        
        # Уведомление мониторинга
        if monitoring_enabled and monitoring_chat_id:
            try:
                from aiogram import Bot
                bot = Bot.get_current()
                await bot.send_message(
                    monitoring_chat_id, 
                    f"🚀 Запуск обработки чанка для команды {team_id}", 
                    parse_mode="Markdown"
                )
            except Exception as e:
                logging.error(f"Ошибка отправки уведомления мониторинга: {e}")
        
        asyncio.create_task(process_chunk(team_id))


async def process_chunk(team_id: str):
    logging.info(f"🔄 Starting chunk processing for team {team_id}")
    
    async with processing_locks[team_id]:
        if len(message_buffer[team_id]) < CHUNK_SIZE:
            logging.warning(f"⏹️ Chunk processing aborted for team {team_id}: buffer size {len(message_buffer[team_id])} < {CHUNK_SIZE}")
            return

        # Get the chunk and clear the buffer for this team
        messages_to_process = message_buffer[team_id][:CHUNK_SIZE]
        message_buffer[team_id] = message_buffer[team_id][CHUNK_SIZE:]
        
        logging.info(f"📦 Processing {len(messages_to_process)} messages for team {team_id}. Remaining in buffer: {len(message_buffer[team_id])}")

    chunk_text = "\n".join(messages_to_process)
    
    try:
        logging.info(f"🧠 Creating embedding for team {team_id} chunk (length: {len(chunk_text)} chars)")
        logging.debug(f"Chunk preview: {chunk_text[:100]}...")
        
        # Get embedding
        vector = await get_embedding(chunk_text)
        logging.info(f"✅ Embedding created successfully for team {team_id} (vector dimension: {len(vector)})")
        
        # Upsert to Pinecone
        vector_id = str(uuid.uuid4())
        logging.info(f"💾 Upserting vector {vector_id} to Pinecone namespace 'team-{team_id}'")
        upsert_vector(vector_id, vector, team_id, chunk_text)
        
        logging.info(f"🎉 Successfully processed and upserted chunk for team {team_id}. Vector ID: {vector_id}")
        
        # Verify the upsert
        from src.services.vector_db import get_namespace_stats
        stats = get_namespace_stats(team_id)
        logging.info(f"📊 Current namespace stats for team {team_id}: {stats['vector_count']} vectors")

    except Exception as e:
        logging.error(f"💥 Error processing chunk for team {team_id}: {e}", exc_info=True)
        # Re-add messages to buffer if processing fails
        logging.info(f"🔄 Re-adding {len(messages_to_process)} messages to buffer for team {team_id}")
        message_buffer[team_id] = messages_to_process + message_buffer[team_id]
        
        # Also log what went wrong specifically
        if "openai" in str(e).lower():
            logging.error(f"🚫 OpenAI API error: Check API key and quota")
        elif "pinecone" in str(e).lower():
            logging.error(f"🚫 Pinecone error: Check API key and index configuration")
        else:
            logging.error(f"🚫 Unknown error type: {type(e).__name__}") 