from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def select_team_keyboard(teams):
    buttons = [
        [InlineKeyboardButton(text=team['name'], callback_data=f"link_chat:{team['$id']}")]
        for team in teams
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def select_chat_team_keyboard(teams):
    buttons = [
        [InlineKeyboardButton(text=team['name'], callback_data=f"chat_with_team:{team['$id']}")]
        for team in teams
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def select_team_for_system_message_keyboard(teams):
    buttons = [
        [InlineKeyboardButton(text=team['name'], callback_data=f"set_system_message:{team['$id']}")]
        for team in teams
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons) 