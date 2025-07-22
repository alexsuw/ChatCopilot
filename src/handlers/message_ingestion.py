import logging
from aiogram import Router, F
from aiogram.types import Message

from src.services.supabase_client import get_linked_chat, save_message

router = Router()

@router.message(F.text & F.chat.type.in_({"group", "supergroup"}))
async def message_handler(message: Message):
    """
    This handler catches all text messages in group chats,
    checks if the chat is linked to a team, and saves the message to Supabase.
    """
    chat_id = message.chat.id
    chat_title = message.chat.title or "Unknown Chat"

    try:
        # Check if the chat is linked to a team
        linked_chat = await get_linked_chat(chat_id)
        if not linked_chat:
            logging.debug(f"Chat {chat_id} ({chat_title}) is not linked to any team. Ignoring message.")
            return

        team_id = linked_chat.get('team_id')
        if not team_id:
            logging.warning(f"Chat {chat_id} ({chat_title}) is linked but has no team_id. Ignoring.")
            return
            
        logging.info(f"Chat {chat_id} is linked to team {team_id}. Saving message.")

        # Save the message to Supabase
        await save_message(
            team_id=team_id,
            chat_id=chat_id,
            message_id=message.message_id,
            user_id=message.from_user.id,
            user_name=message.from_user.full_name,
            text=message.text
        )

    except Exception as e:
        logging.error(f"Error processing message in chat {chat_id}: {e}", exc_info=True)