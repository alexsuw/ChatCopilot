from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def create_teams_keyboard(teams, action_prefix=""):
    """
    Универсальная функция для создания клавиатуры команд с префиксом
    """
    buttons = [
        [InlineKeyboardButton(text=f"💬 Диалог с {team['name']}", callback_data=f"{action_prefix}:{team['id']}")]
        for team in teams
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def select_team_keyboard(teams):
    buttons = [
        [InlineKeyboardButton(text=team['name'], callback_data=f"link_chat:{team['id']}")]
        for team in teams
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def select_chat_team_keyboard(teams):
    buttons = [
        [InlineKeyboardButton(text=f"💬 Диалог с {team['name']}", callback_data=f"chat_with_team:{team['id']}")]
        for team in teams
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def select_team_for_system_message_keyboard(teams):
    buttons = [
        [InlineKeyboardButton(text=team['name'], callback_data=f"set_system_message:{team['id']}")]
        for team in teams
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons) 