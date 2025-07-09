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
    chat_title = message.chat.title or "Unknown Chat"
    
    logging.info(f"Processing message from chat {chat_id} ({chat_title})")
    
    try:
        # Get linked chat document
        chat_doc = await get_linked_chat(chat_id)
        if not chat_doc:
            # Chat not linked to any team, ignore.
            logging.debug(f"Chat {chat_id} ({chat_title}) not linked to any team, ignoring message")
            return
        
        team_id = chat_doc['team_id']
        logging.info(f"Chat {chat_id} ({chat_title}) is linked to team {team_id}")
        
    except Exception as e:
        # Chat not linked to any team, ignore.
        logging.warning(f"Error getting linked chat for {chat_id} ({chat_title}): {e}")
        return

    if not team_id:
        logging.warning(f"Chat {chat_id} ({chat_title}) has empty team_id, ignoring")
        return # Ignore messages from chats not linked to any team

    # Add message to buffer
    full_message = f"{message.from_user.first_name}: {message.text}"
    message_buffer[team_id].append(full_message)
    
    current_buffer_size = len(message_buffer[team_id])
    logging.info(f"Added message to team {team_id} buffer. Current size: {current_buffer_size}/{CHUNK_SIZE}")

    # If buffer is full, process the chunk
    if current_buffer_size >= CHUNK_SIZE:
        logging.info(f"Buffer full for team {team_id}, processing chunk")
        asyncio.create_task(process_chunk(team_id))


async def process_chunk(team_id: str):
    logging.info(f"Starting chunk processing for team {team_id}")
    
    async with processing_locks[team_id]:
        if len(message_buffer[team_id]) < CHUNK_SIZE:
            logging.warning(f"Chunk processing aborted for team {team_id}: buffer size {len(message_buffer[team_id])} < {CHUNK_SIZE}")
            return

        # Get the chunk and clear the buffer for this team
        messages_to_process = message_buffer[team_id][:CHUNK_SIZE]
        message_buffer[team_id] = message_buffer[team_id][CHUNK_SIZE:]
        
        logging.info(f"Processing {len(messages_to_process)} messages for team {team_id}. Remaining in buffer: {len(message_buffer[team_id])}")

    chunk_text = "\n".join(messages_to_process)
    
    try:
        logging.info(f"Creating embedding for team {team_id} chunk (length: {len(chunk_text)} chars)")
        # Get embedding
        vector = await get_embedding(chunk_text)
        
        # Upsert to Pinecone
        vector_id = str(uuid.uuid4())
        logging.info(f"Upserting vector {vector_id} for team {team_id}")
        upsert_vector(vector_id, vector, team_id, chunk_text)
        
        logging.info(f"Successfully processed and upserted chunk for team {team_id}. Vector ID: {vector_id}")

    except Exception as e:
        logging.error(f"Error processing chunk for team {team_id}: {e}", exc_info=True)
        # Re-add messages to buffer if processing fails
        logging.info(f"Re-adding {len(messages_to_process)} messages to buffer for team {team_id}")
        message_buffer[team_id] = messages_to_process + message_buffer[team_id] 