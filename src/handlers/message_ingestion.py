import asyncio
import logging
import uuid
from collections import defaultdict
from aiogram import Router, F
from aiogram.types import Message

from src.services.supabase_client import get_linked_chat
from src.services.vector_db import get_embedding, upsert_vector

router = Router()
router.message.filter(F.chat.type.in_({"group", "supergroup"}))

# In-memory buffer for messages
# {team_id: [message_text_1, message_text_2, ...]}
message_buffer = defaultdict(list)
# To avoid processing the same chunk multiple times
processing_locks = defaultdict(asyncio.Lock)

CHUNK_SIZE = 5  # Number of messages to batch together

@router.message(F.text)
async def message_handler(message: Message):
    chat_id = message.chat.id
    
    try:
        # Get linked chat document
        chat_doc = await get_linked_chat(chat_id)
        if not chat_doc:
            # Chat not linked to any team, ignore.
            return
        team_id = chat_doc['team_id']
    except Exception:
        # Chat not linked to any team, ignore.
        return

    if not team_id:
        return # Ignore messages from chats not linked to any team

    # Add message to buffer
    full_message = f"{message.from_user.first_name}: {message.text}"
    message_buffer[team_id].append(full_message)

    # If buffer is full, process the chunk
    if len(message_buffer[team_id]) >= CHUNK_SIZE:
        asyncio.create_task(process_chunk(team_id))


async def process_chunk(team_id: str):
    async with processing_locks[team_id]:
        if len(message_buffer[team_id]) < CHUNK_SIZE:
            return

        # Get the chunk and clear the buffer for this team
        messages_to_process = message_buffer[team_id][:CHUNK_SIZE]
        message_buffer[team_id] = message_buffer[team_id][CHUNK_SIZE:]

    chunk_text = "\n".join(messages_to_process)
    
    try:
        # Get embedding
        vector = await get_embedding(chunk_text)
        
        # Upsert to Pinecone
        vector_id = str(uuid.uuid4())
        upsert_vector(vector_id, vector, team_id, chunk_text)
        
        logging.info(f"Successfully processed and upserted a chunk for team {team_id}.")

    except Exception as e:
        logging.error(f"Error processing chunk for team {team_id}: {e}", exc_info=True)
        # Optional: re-add messages to buffer if processing fails
        # message_buffer[team_id] = messages_to_process + message_buffer[team_id] 